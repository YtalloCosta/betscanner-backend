import os
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
from datetime import datetime

from models.odds import Odds
from utils.dedupe import dedupe_add

# SCRAPERS
from scrapers.betano import BetanoScraper
from scrapers.bwin import BwinScraper
from scrapers.kto import KTOScraper
from scrapers.pinnacle import PinnacleScraper
from scrapers.stake import StakeScraper
from scrapers.xb1 import OneXBetScraper
from scrapers.xb22 import TwentyTwoBetScraper
from scrapers.sportingbet import SportingbetScraper

from services.surebet import detect_surebets


# ==============================
# CONFIG
# ==============================
API_KEY = os.getenv("BETSCANNER_API_KEY", None)
SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL_SECONDS", "120"))
DEFAULT_DAYS_AHEAD = int(os.getenv("DEFAULT_DAYS_AHEAD", "3"))

app = FastAPI(title="BetScanner API")

# CORS liberado
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage global
ODDS_STORE: List[Dict] = []
STORE_LOCK = asyncio.Lock()

# Lista oficial de scrapers
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
# EXECUTAR SCRAPERS
# ==============================
async def run_scrapers(days_ahead: int = DEFAULT_DAYS_AHEAD) -> int:
    tasks = []

    async def run_one(scr):
        try:
            print(f"[SCRAPER] Iniciando {scr.name}")
            return await asyncio.wait_for(scr.fetch_upcoming(days_ahead), timeout=60)
        except asyncio.TimeoutError:
            print(f"[TIMEOUT] {scr.name}")
            return []
        except Exception as e:
            print(f"[ERRO] {scr.name}: {e}")
            return []

    for s in SCRAPERS:
        tasks.append(run_one(s))

    results = await asyncio.gather(*tasks)

    # Normalização e dedupe
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

    print(f"[SCRAPERS] {added} odds adicionadas.")
    return added


# ==============================
# LOOP AUTOMÁTICO
# ==============================
@app.on_event("startup")
async def startup_event():
    app.state.scrape_task = asyncio.create_task(periodic_scrape())


@app.on_event("shutdown")
async def shutdown_event():
    task = getattr(app.state, "scrape_task", None)
    if task:
        task.cancel()


async def periodic_scrape():
    while True:
        try:
            await run_scrapers()
        except Exception as e:
            print("[SCRAPER LOOP ERROR]", e)

        await asyncio.sleep(SCRAPE_INTERVAL)


# ==============================
# VALUE BETS
# ==============================
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
# ENDPOINTS OFICIAIS
# ==============================

@app.get("/")
async def root():
    return {"status": "ok", "message": "BetScanner API is running."}


@app.get("/surebets")
async def api_surebets():
    try:
        sb = detect_surebets(ODDS_STORE, min_profit_pct=0.1)
        return {"count": len(sb), "surebets": sb}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/valuebets")
async def api_valuebets():
    try:
        vb = detect_valuebets(ODDS_STORE)
        return {"count": len(vb), "valuebets": vb}
    except Exception as e:
        raise HTTPException(500, str(e))


# ==============================
# ENDPOINT PARA TESTAR SCRAPERS
# ==============================
@app.get("/_force_scrape")
async def force_scrape():
    added = await run_scrapers()
    return {"added": added, "total_odds": len(ODDS_STORE)}
