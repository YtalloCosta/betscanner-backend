import os
import asyncio
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict
from datetime import datetime

from models.odds import Odds
from utils.dedupe import dedupe_add

# ============================
# IMPORT SCRAPERS
# ============================
from scrapers.betano import BetanoScraper
from scrapers.bwin import BwinScraper
from scrapers.kto import KTOScraper
from scrapers.pinnacle import PinnacleScraper
from scrapers.stake import StakeScraper
from scrapers.xb1 import OneXBetScraper
from scrapers.xb22 import TwentyTwoBetScraper
from scrapers.sportingbet import SportingbetScraper

# ============================
# CONFIG GLOBAL
# ============================
API_KEY = os.getenv("BETSCANNER_API_KEY", None)
SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL_SECONDS", "60"))
DEFAULT_DAYS_AHEAD = int(os.getenv("DEFAULT_DAYS_AHEAD", "7"))

app = FastAPI(title="BetScanner Realtime API")

# Liberar CORS para o Lovable
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================
# GLOBAL STORE
# ============================
ODDS_STORE: List[Dict] = []
STORE_LOCK = asyncio.Lock()

# ============================
# SCRAPERS LIST
# ============================
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


# ============================
# VERIFY API KEY (OPTIONAL)
# ============================
async def verify_api_key(x_api_key: str = Header(None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key


# ============================
# RUN SCRAPERS
# ============================
async def run_scrapers(days_ahead: int = DEFAULT_DAYS_AHEAD) -> int:
    print("\n===== INICIANDO SCRAPERS =====")

    tasks = []

    async def run_one(scraper):
        try:
            print(f"[SCRAPER] Executando: {scraper.name}")
            result = await asyncio.wait_for(scraper.fetch_upcoming(days_ahead), timeout=45)
            print(f"[SCRAPER] {scraper.name} → OK ({len(result)} odds)")
            return result
        except asyncio.TimeoutError:
            print(f"[SCRAPER] {scraper.name} → TIMEOUT")
            return []
        except Exception as e:
            print(f"[SCRAPER] {scraper.name} → ERRO: {e}")
            return []

    for scraper in SCRAPERS:
        tasks.append(run_one(scraper))

    results = await asyncio.gather(*tasks)

    new_list = []

    for res in results:
        for o in res:
            if isinstance(o, Odds):
                new_list.append(o.dict())
            else:
                new_list.append(o)

    async with STORE_LOCK:
        added = dedupe_add(ODDS_STORE, new_list)

    print(f"[SCRAPERS] Finalizado. Novas odds adicionadas: {added}")
    return added


# ============================
# PERIÓDICO (LOOP) — Modo Railway
# ============================
async def periodic_scrape():
    await asyncio.sleep(3)  # Delay inicial para garantir que o servidor subiu

    print("=== LOOP DE SCRAPING INICIADO ===")

    while True:
        try:
            added = await run_scrapers()
            print(f"[LOOP] {added} odds adicionadas às {datetime.utcnow().isoformat()}Z")
        except Exception as e:
            print(f"[LOOP ERRO] {e}")

        await asyncio.sleep(SCRAPE_INTERVAL)


@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_event_loop()
    loop.create_task(periodic_scrape())
    print(">> Startup executado — LOOP DO SCRAPER INICIADO")


# ============================
# DETECT SUREBETS
# ============================
from services.surebet import detect_surebets


# ============================
# DETECT VALUE BETS
# ============================
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


# ============================
# ENDPOINTS
# ============================
@app.get("/surebets")
async def api_surebets():
    sb = detect_surebets(ODDS_STORE, min_profit_pct=0.1)
    return {"count": len(sb), "surebets": sb}


@app.get("/valuebets")
async def api_valuebets():
    vb = detect_valuebets(ODDS_STORE)
    return {"count": len(vb), "valuebets": vb}


# ============================
# TESTAR MANUALMENTE O SCRAPING
# ============================
@app.get("/_force_scrape")
async def force_scrape():
    added = await run_scrapers()
    return {"added": added, "total_odds": len(ODDS_STORE)}


# ============================
# HEALTHCHECK
# ============================
@app.get("/")
async def root():
    return {"status": "ok", "message": "BetScanner API is running."}
