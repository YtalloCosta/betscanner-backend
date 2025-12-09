from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os

app = FastAPI(title="BetScanner API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth via API Key
API_KEY = os.getenv("BETSCANNER_API_KEY", "your-secret-key")

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key

# Models
class OddsData(BaseModel):
    home_team: str
    away_team: str
    league: str
    sport: str
    market: str
    selection: str
    odds: float
    bookmaker: str
    timestamp: str

class SureBet(BaseModel):
    home_team: str
    away_team: str
    league: str
    profit_percentage: float
    bets: List[dict]

class ValueBet(BaseModel):
    home_team: str
    away_team: str
    league: str
    expected_value: float
    odds: float
    bookmaker: str
    market: str
    selection: str

# Endpoints
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/odds", dependencies=[Depends(verify_api_key)])
async def get_odds(sport: Optional[str] = None, league: Optional[str] = None):
    # TODO: Implementar scraping real
    # Por enquanto, retorna dados mock
    return {"odds": [], "last_updated": "2024-01-01T00:00:00Z"}

@app.get("/surebets", dependencies=[Depends(verify_api_key)])
async def get_surebets(
    min_profit: Optional[float] = 0.5,
    sport: Optional[str] = None
):
    # TODO: Implementar detecção de surebets
    return {"surebets": [], "count": 0}

@app.get("/valuebets", dependencies=[Depends(verify_api_key)])
async def get_valuebets(
    min_ev: Optional[float] = 2.0,
    sport: Optional[str] = None
):
    # TODO: Implementar detecção de valuebets
    return {"valuebets": [], "count": 0}

@app.post("/scrape", dependencies=[Depends(verify_api_key)])
async def trigger_scrape(bookmakers: Optional[List[str]] = None):
    # TODO: Disparar scraping manual
    return {"status": "scraping_started"}
