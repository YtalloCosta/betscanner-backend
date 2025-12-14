import os
import asyncio
from fastapi import FastAPI, HTTPException, Depends, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict
from datetime import datetime
from models.odds import Odds
from utils.dedupe import dedupe_add

# scrapers reais e templates
from scrapers.betano import BetanoScraper
from scrapers.sportingbet import SportingbetScraper
from scrapers.kto import KTOScraper
from scrapers.bet365_template import Bet365ScraperTemplate
from scrapers.pinnacle_template import PinnacleScraperTemplate
from scrapers.betfair_template import BetfairScraperTemplate
from scrapers.x1bet_template import OneXBetScraperTemplate

API_KEY = os.getenv("BETSCANNER_API_KEY", None)
SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL_SECONDS", "60"))
DEFAULT_DAYS_AHEAD = int(os.getenv("DEFAULT_DAYS_AHEAD", "7"))

app = FastAPI(title="BetScanner Realtime")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def verify_api_key(x_api_key: str = Header(...)):
    if API_KEY is None:
        return x_api_key
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key

ODDS_STORE: List[Dict] = []
STORE_LOCK = asyncio.Lock()

SCRAPERS = [
    BetanoScraper(),
    SportingBetScraper(),  # Corrigido aqui
    KTOScraper(),
    Bet365ScraperTemplate(),
    PinnacleScraperTemplate(),
    BetfairScraperTemplate(),
    OneXBetScraperTemplate(),
]

async def run_scrapers(days_ahead: int = DEFAULT_DAYS_AHEAD) -> int:
    tasks = []
    for s in SCRAPERS:
        async def run_one(scr):
            try:
                return await asyncio.wait_for(scr.fetch_upcoming(days_ahead=days_ahead), timeout=45)
            except asyncio.TimeoutError:
                print(f"[scraper:{scr.name}] timeout")
                return []
            except Exception as e:
                print(f"[scraper:{scr.name}] error: {e}")
                return []
        tasks.append(run_one(s))

    results = await asyncio.gather(*tasks, return_exceptions=False)

    new_items = []
    for res in results:
        if isinstance(res, list):
            for o in res:
                if isinstance(o, Odds):
                    new_items.append(o.dict())
                elif isinstance(o, dict):
                    new_items.append(o)
                else:
                    try:
                        new_items.append(o.dict())
                    except Exception:
                        continue

    async with STORE_LOCK:
        added = dedupe_add(ODDS_STORE, new_items)

    try:
        from services.surebet import detect_surebets
        surebets = detect_surebets(ODDS_STORE, min_profit_pct=0.1)
    except Exception:
        surebets = []

    asyncio.create_task(manager.broadcast({"type": "surebets_update", "count": len(surebets), "data": surebets}))
    return added

@app.on_event("startup")
async def startup_event():
    app.state.scrape_task = asyncio.create_task(periodic_scrape())

@app.on_event("shutdown")
async def shutdown_event():
    task = getattr(app.state, "scrape_task", None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

async def periodic_scrape():
    while True:
        try:
            added = await run_scrapers(days_ahead=DEFAULT_DAYS_AHEAD)
            print(f"[periodic_scrape] added {added} odds at {datetime.utcnow().isoformat()}Z")
        except Exception as e:
            print("[periodic_scrape] error:", e)
        await asyncio.sleep(SCRAPE_INTERVAL)
