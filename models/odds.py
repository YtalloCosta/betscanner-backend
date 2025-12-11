from pydantic import BaseModel
from typing import Optional

class Odds(BaseModel):
    event_id: str
    home_team: str
    away_team: str
    league: str
    sport: str = "soccer"
    market: str  # ex "1X2"
    selection: str  # "home", "away", "draw", etc
    odds: float
    bookmaker: str
    timestamp: str
    start_time: Optional[str] = None
