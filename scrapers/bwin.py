import aiohttp
import uuid
from datetime import datetime
from typing import List

from scrapers.base import BaseScraper
from models.odds import Odds


API = (
    "https://gaming-int.bwin.com/cms/api/event?"
    "lang=pt-br&sportIds=4&isHighlighted=false&skip=0&take=50"
)


class BwinScraper(BaseScraper):
    name = "bwin"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        out: List[Odds] = []

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API, timeout=15) as resp:
                    data = await resp.json()

            events = data.get("events", [])
            for ev in events:
                try:
                    home = ev["participants"][0]["name"]
                    away = ev["participants"][1]["name"]
                    league = ev["competition"]["name"]

                    markets = ev.get("markets", [])
                    if not markets:
                        continue

                    outcomes = markets[0].get("outcomes", [])
                    if len(outcomes) < 2:
                        continue

                    odd_home = float(outcomes[0]["odds"])
                    odd_away = float(outcomes[1]["odds"])

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
            print(f"[BWIN] erro: {e}")

        return out
