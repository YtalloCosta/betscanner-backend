from pydantic import BaseModel

class Odds(BaseModel):
    home_team: str
    away_team: str
    league: str
    sport: str
    market: str
    selection: str
    odds: float
    bookmaker: str
    timestamp: str
