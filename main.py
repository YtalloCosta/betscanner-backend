import os
import asyncio
from fastapi import FastAPI, HTTPException, Depends, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict
from datetime import datetime

from models.odds import Odds

# 🔥 IMPORTA A NORMALIZAÇÃO COMPLETA
from utils.normalize import (
    clean_team_name,
    clean_league_name,
    clean_market_name,
    clean_selection_name
)

# 🔥 IMPORTA DEDUPLICAÇÃO OTIMIZADA
from utils.dedupe import dedupe_add

# ========== SCRAPERS ==========
from scrapers.betano import BetanoScraper
from scrapers.sportingbet import SportingbetScraper
from scrapers.kto import KTOScraper
from scrapers.bet365_template import Bet365ScraperTemplate
from scrapers.pinnacle_template import PinnacleScraperTemplate
from scrapers.betfair_template import BetfairScraperTemplate
from scrapers.x1bet_template import OneXBetScraperTemplate


# ========== CONFIG ==========
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


# ========== AUTH ==========
async def verify_api_key(x_api_key: str = Header(...)):
    if API_KEY is None:
        return x_api_key
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key


# ========== STORAGE ==========
ODDS_STORE: List[Dict] = []
STORE_LOCK = asyncio.Lock()


# ========== WEBSOCKET MANAGER ==========
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: Dict):
        to_remove = []
        for ws in list(self.active):
            try:
                await ws.send_json(message)
            except Exception:
                to_remove.append(ws)
        for r in to_remove:
            self.disconnect(r)


manager = ConnectionManager()


# ========== STARTUP ==========
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


# ========== SCRAPERS ==========
SCRAPERS = [
    BetanoScraper(),
    SportingBetScraper(),
    KTOScraper(),
    Bet365ScraperTemplate(),
    PinnacleScraperTemplate(),
    BetfairScraperTemplate(),
    OneXBetScraperTemplate(),
]


# ========== RUN SCRAPERS ==========
async def run_scrapers(days_ahead: int = DEFAULT_DAYS_AHEAD) -> int:

    async def run_one(scr):
        try:
            return await asyncio.wait_for(scr.fetch_upcoming(days_ahead=days_ahead), timeout=45)
        except asyncio.TimeoutError:
            print(f"[scraper:{scr.name}] timeout")
            return []
        except Exception as e:
            print(f"[scraper:{scr.name}] error: {e}")
            return []

    tasks = [run_one(s) for s in SCRAPERS]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    new_items = []

    for res in results:
        if isinstance(res, list):
            for o in res:

                # ===========================
                # 🔥 NORMALIZAÇÃO APLICADA AQUI
                # ===========================
                if isinstance(o, Odds):
                    d = o.dict()
                elif isinstance(o, dict):
                    d = o
                else:
                    try:
                        d = o.dict()
                    except:
                        continue

                # NORMALIZAÇÕES PROFISSIONAIS
                d["home_team"] = clean_team_name(d.get("home_team", ""))
                d["away_team"] = clean_team_name(d.get("away_team", ""))

                if "league" in d:
                    d["league"] = clean_league_name(d["league"])

                if "market" in d:
                    d["market"] = clean_market_name(d["market"])

                if "selection" in d:
                    d["selection"] = clean_selection_name(d["selection"])

                new_items.append(d)

    # ========== INSERE COM DEDUP ==========
    async with STORE_LOCK:
        added = dedupe_add(ODDS_STORE, new_items)

    # ========== DETECTA SUREBETS ==========
    try:
        from services.surebet import detect_surebets
        surebets = detect_surebets(ODDS_STORE, min_profit_pct=0.1)
    except Exception:
        surebets = []

    asyncio.create_task(
        manager.broadcast({"type": "surebets_update", "count": len(surebets), "data": surebets})
    )

    return added


# ========== LOOP DE SCRAPE ==========
async def periodic_scrape():
    while True:
        try:
            added = await run_scrapers(days_ahead=DEFAULT_DAYS_AHEAD)
            print(f"[periodic_scrape] added {added} odds at {datetime.utcnow().isoformat()}Z")
        except Exception as e:
            print("[periodic_scrape] error:", e)

        await asyncio.sleep(SCRAPE_INTERVAL)


# ========== ROTAS ==========
@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z"}


@app.get("/odds", dependencies=[Depends(verify_api_key)])
async def get_odds(sport: Optional[str] = None, league: Optional[str] = None):
    async with STORE_LOCK:
        data = list(ODDS_STORE)

    if sport:
        data = [d for d in data if d.get("sport") == sport]
    if league:
        data = [d for d in data if d.get("league") == league]

    return {"count": len(data), "odds": data}


@app.post("/scrape", dependencies=[Depends(verify_api_key)])
async def trigger_scrape(days_ahead: Optional[int] = DEFAULT_DAYS_AHEAD):
    added = await run_scrapers(days_ahead=days_ahead)
    return {"status": "ok", "added": added}


@app.get("/surebets", dependencies=[Depends(verify_api_key)])
async def get_surebets(min_profit: Optional[float] = 0.1):
    async with STORE_LOCK:
        data = list(ODDS_STORE)

    from services.surebet import detect_surebets
    res = detect_surebets(data, min_profit_pct=min_profit)

    return {"count": len(res), "surebets": res}


@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
