import os
import asyncio
from fastapi import FastAPI, HTTPException, Depends, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict
from datetime import datetime

from models.odds import Odds
from utils.dedupe import dedupe_add

# ==============================
# IMPORT SCRAPERS
# ==============================
from scrapers.betano import BetanoScraper
from scrapers.bwin import BwinScraper
from scrapers.kto import KTOScraper
from scrapers.pinnacle import PinnacleScraper
from scrapers.stake import StakeScraper
from scrapers.xb1 import OneXBetScraper
from scrapers.xb22 import TwentyTwoBetScraper
from scrapers.sportingbet import SportingbetScraper

# ==============================
# CONFIG GLOBAL
# ==============================
API_KEY = os.getenv("BETSCANNER_API_KEY", None)
SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL_SECONDS", "60"))
DEFAULT_DAYS_AHEAD = int(os.getenv("DEFAULT_DAYS_AHEAD", "7"))

app = FastAPI(title="BetScanner Realtime API")

# CORS liberado totalmente para o Lovable
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================
# API KEY VERIFICATION
# ==============================
async def verify_api_key(x_api_key: str = Header(...)):
    if API_KEY is None:
        return x_api_key  # sem API KEY configurada → libera tudo
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key

# ==============================
# GLOBAL ODDS STORAGE
# ==============================
ODDS_STORE: List[Dict] = []
STORE_LOCK = asyncio.Lock()

# ==============================
# SCRAPER LIST
# ==============================
SCRAPERS = [
    BetanoScraper(),
    BwinScraper(),
    KTOScraper(),
    PinnacleScraper(),
    StakeScraper(),
    OneXBetScraper(),
    TwentyTwoBetScraper(),
    SportingbetScraper(),  # Agora adicionado corretamente
]


# ==============================
# RUN SCRAPERS
# ==============================
async def run_scrapers(days_ahead: int = DEFAULT_DAYS_AHEAD) -> int:
    tasks = []

    for s in SCRAPERS:

        async def run_one(scr):
            try:
                return await asyncio.wait_for(scr.fetch_upcoming(days_ahead=days_ahead), timeout=45)
            except asyncio.TimeoutError:
                print(f"[scraper:{scr.name}] Timeout")
                return []
            except Exception as e:
                print(f"[scraper:{scr.name}] Error: {e}")
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
                    except:
                        continue

    async with STORE_LOCK:
        added = dedupe_add(ODDS_STORE, new_items)

    return added


# ==============================
# STARTUP: AUTO SCRAPER LOOP
# ==============================
@app.on_event("startup")
async def startup_event():
    print("Starting periodic scraping...")
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
            print(f"[SCRAPER LOOP] Added {added} odds at {datetime.utcnow().isoformat()}Z")
        except Exception as e:
            print("[SCRAPER LOOP ERROR]:", e)

        await asyncio.sleep(SCRAPE_INTERVAL)


# ==============================
# HELPER: DETECT SUREBETS
# ==============================
from services.surebet import detect_surebets


# ==============================
# HELPER: DETECT VALUE BETS
# ==============================
def detect_valuebets(odds_list, threshold_pct=5):
    """
    EXEMPLO simples de detecção de value bet.
    Você poderá substituir mais tarde pela sua regra oficial.
    """
    results = []

    for o in odds_list:
        try:
            prob = 1 / float(o["odds"])  # probabilidade implícita
            fair = 1 / prob
            diff_pct = ((o["odds"] - fair) / fair) * 100

            if diff_pct >= threshold_pct:
                results.append({
                    "event": f"{o['home_team']} vs {o['away_team']}",
                    "market": o["market"],
                    "selection": o["selection"],
                    "bookmaker": o["bookmaker"],
                    "odds": o["odds"],
                    "value_pct": round(diff_pct, 2),
                })
        except:
            continue

    return results


# ==============================
# ENDPOINTS REQUERIDOS PELO LOVABLE
# ==============================

@app.get("/surebets")
async def api_surebets():
    """Retorna todas as surebets detectadas."""
    try:
        sb = detect_surebets(ODDS_STORE, min_profit_pct=0.1)
        return {"count": len(sb), "surebets": sb}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/valuebets")
async def api_valuebets():
    """Retorna oportunidades de value bet."""
    try:
        vb = detect_valuebets(ODDS_STORE)
        return {"count": len(vb), "valuebets": vb}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================
# HEALTH CHECK (IMPORTANTE PARA RAILWAY)
# ==============================
@app.get("/")
async def root():
    return {"status": "ok", "message": "BetScanner API is running."}
