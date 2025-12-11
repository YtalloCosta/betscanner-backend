from .base import BaseScraper
from ..models.odds import Odds
from datetime import datetime, timedelta
from typing import List
import uuid

class MockScraper(BaseScraper):
    name = "mockbook"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        now = datetime.utcnow()
        out: List[Odds] = []
        # create 3 sample matches per day for a few days (demo)
        for day in range(1, min(8, days_ahead+1)):
            start = now + timedelta(days=day)
            for match_i in range(1, 3):
                event_id = str(uuid.uuid4())
                out.append(Odds(
                    event_id=event_id,
                    home_team=f"MockHome{day}{match_i}",
                    away_team=f"MockAway{day}{match_i}",
                    league="Mock League",
                    market="1X2",
                    selection="home",
                    odds=1.8 + 0.05*match_i,
                    bookmaker=self.name,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    start_time=start.isoformat() + "Z"
                ))
                out.append(Odds(
                    event_id=event_id,
                    home_team=f"MockHome{day}{match_i}",
                    away_team=f"MockAway{day}{match_i}",
                    league="Mock League",
                    market="1X2",
                    selection="away",
                    odds=3.1 + 0.1*match_i,
                    bookmaker=self.name,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    start_time=start.isoformat() + "Z"
                ))
        return out
