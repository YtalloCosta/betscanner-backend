import os
import asyncio
from fastapi import FastAPI, HTTPException, Depends, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict
from datetime import datetime
from models.odds import Odds
from scrapers.playwright_template import PlaywrightScraper
scraper = PlaywrightScraper()
from services.surebet import detect_surebets
from utils.dedupe import dedupe_add

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

async def run_scrapers(days_ahead: int = DEFAULT_DAYS_AHEAD) -> int:
    # add real scrapers to this list, e.g. PlaywrightTemplateScraper(), Bet365Scraper(), BetanoScraper()
    scrapers = [MockScraper()]
    new_items = []
    for s in scrapers:
        fetched = await s.fetch_upcoming(days_ahead=days_ahead)
        for o in fetched:
            new_items.append(o.dict())
    async with STORE_LOCK:
        added = dedupe_add(ODDS_STORE, new_items)
    surebets = detect_surebets(ODDS_STORE, min_profit_pct=0.1)
    # broadcast (non-blocking)
    asyncio.create_task(manager.broadcast({"type": "surebets_update", "count": len(surebets), "data": surebets}))
    return added

async def periodic_scrape():
    while True:
        try:
            await run_scrapers(days_ahead=DEFAULT_DAYS_AHEAD)
        except Exception:
            # in production, log the exception
            pass
        await asyncio.sleep(SCRAPE_INTERVAL)

@app.get("/health")
async def health():
    return {"status":"ok","timestamp": datetime.utcnow().isoformat()+"Z"}

@app.get("/odds", dependencies=[Depends(verify_api_key)])
async def get_odds(sport: Optional[str] = None, league: Optional[str] = None):
    async with STORE_LOCK:
        data = list(ODDS_STORE)
    if sport:
        data = [d for d in data if d.get("sport")==sport]
    if league:
        data = [d for d in data if d.get("league")==league]
    return {"count": len(data), "odds": data}

@app.post("/scrape", dependencies=[Depends(verify_api_key)])
async def trigger_scrape(days_ahead: Optional[int] = DEFAULT_DAYS_AHEAD):
    added = await run_scrapers(days_ahead=days_ahead)
    return {"status":"ok","added": added}

@app.get("/surebets", dependencies=[Depends(verify_api_key)])
async def get_surebets(min_profit: Optional[float] = 0.1):
    async with STORE_LOCK:
        data = list(ODDS_STORE)
    res = detect_surebets(data, min_profit_pct=min_profit)
    return {"count": len(res), "surebets": res}

@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # keep connection alive — optionally receive commands
            msg = await websocket.receive_text()
            # ignoring messages for now
    except WebSocketDisconnect:
        manager.disconnect(websocket)

