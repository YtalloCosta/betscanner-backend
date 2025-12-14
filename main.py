import os
import asyncio
from fastapi import FastAPI, HTTPException, Depends, Header
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
# CONFIG
# ==============================
API_KEY = os.getenv("BETSCANNER_API_KEY", None)
DEFAULT_DAYS_AHEAD = int(os.getenv("DEFAULT_DAYS_AHEAD", "7"))

app = FastAPI(title="BetScanner API")

# CORS liberado totalmente
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
        return x_api_key
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
    SportingbetScraper(),
]

# ==============================
# RUN SCRAPERS (Manual)
# ==============================
async def run_scrapers(days_ahead: int = DEFAULT_DAYS_AHEAD) -> int:
    tasks = []

    for s in SCRAPERS:
        async def run_one(scr):
            try:
                return await asyncio.wait_for(scr.fetch_upcoming(days_ahead=days_ahead), timeout=45)
            except Exception as e:
                print(f"[scraper:{scr.name}] Error:", e)
                return []

        tasks.append(run_one(s))

    results = await asyncio.gather(*tasks)

    new_items = []
    for res in results:
        if isinstance(res, list):
            for o in res:
                if isinstance(o, Odds):
                    new_items.append(o.dict())
                elif isinstance(o, dict):
                    new_items.append(o)

    async with STORE_LOCK:
        added = dedupe_add(ODDS_STORE, new_items)

    return added

# ==============================
# IMPORT DETECTORS
# ==============================
from services.surebet import detect_surebets

def detect_valuebets(odds_list, threshold_pct=5):
    results = []
    for o in odds_list:
        try:
            prob = 1 / float(o["odds"])
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
# ENDPOINT PARA ACIONAR SCRAPERS MANUALMENTE
# ==============================
@app.post("/scrape")
async def api_scrape():
    added = await run_scrapers()
    return {"added": added, "total_odds": len(ODDS_STORE)}

# ==============================
# ENDPOINTS REQUERIDOS PELO LOVABLE
# ==============================
@app.get("/surebets")
async def api_surebets():
    sb = detect_surebets(ODDS_STORE, min_profit_pct=0.1)
    return {"count": len(sb), "surebets": sb}

@app.get("/valuebets")
async def api_valuebets():
    vb = detect_valuebets(ODDS_STORE)
    return {"count": len(vb), "valuebets": vb}

# ==============================
# HEALTH CHECK
# ==============================
@app.get("/")
async def root():
    return {"status": "ok", "message": "BetScanner API is running."}
