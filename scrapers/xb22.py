import aiohttp
import uuid
from datetime import datetime
from typing import List

from scrapers.base import BaseScraper
from models.odds import Odds


API_URL = "https://22bet.com/LineFeed/Get1x2?sport=1&count=50&lng=en&isGuest=1"


class TwentyTwoBetScraper(BaseScraper):
    name = "22bet"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        out: List[Odds] = []

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API_URL, timeout=15) as resp:
                    data = await resp.json()

            events = data.get("Value", [])
            for ev in events:
                try:
                    home = ev["O1"]
                    away = ev["O2"]
                    league = ev.get("L", "")

                    odds = ev.get("E", [])
                    if len(odds) < 2:
                        continue

                    odd_home = float(odds[0]["C"])
                    odd_away = float(odds[1]["C"])

                    timestamp = datetime.utcnow().isoformat() + "Z"

                    out.append(Odds(
                        event_id=str(uuid.uuid4()),
                        home_team=home,
                        away_team=away,
                        league=league,
                        market="1x2",
                        selection="home",
                        odds=odd_home,
                        bookmaker=self.name,
                        timestamp=timestamp,
                    ))

                    out.append(Odds(
                        event_id=str(uuid.uuid4()),
                        home_team=home,
                        away_team=away,
                        league=league,
                        market="1x2",
                        selection="away",
                        odds=odd_away,
                        bookmaker=self.name,
                        timestamp=timestamp,
                    ))

                except Exception:
                    continue

        except Exception as e:
            print(f"[22BET] erro: {e}")

        return out
