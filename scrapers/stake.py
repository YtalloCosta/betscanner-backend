import aiohttp
import uuid
from datetime import datetime
from typing import List

from scrapers.base import BaseScraper
from models.odds import Odds


class StakeScraper(BaseScraper):
    name = "stake"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        """
        Scraper real usando a API pública da Stake.
        Retorna eventos de futebol com odds 1x2.
        """
        out: List[Odds] = []

        url = (
            "https://api.stake.com/sports/events?"
            "sport=soccer&"
            f"limit=50&" 
            "marketType=match_odds"
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as resp:
                    data = await resp.json()

            events = data.get("events", [])
            for ev in events:
                try:
                    home = ev["homeTeam"]["name"]
                    away = ev["awayTeam"]["name"]
                    league = ev["competition"]["name"]

                    markets = ev.get("markets", [])
                    if not markets:
                        continue

                    outcomes = markets[0].get("outcomes", [])
                    if len(outcomes) < 2:
                        continue

                    odd_home = float(outcomes[0]["price"])
                    odd_away = float(outcomes[1]["price"])

                    out.append(
                        Odds(
                            event_id=str(uuid.uuid4()),
                            home_team=home,
                            away_team=away,
                            league=league,
                            market="1x2",
                            selection="home",
                            odds=odd_home,
                            bookmaker=self.name,
                            timestamp=datetime.utcnow().isoformat() + "Z",
                        )
                    )

                    out.append(
                        Odds(
                            event_id=str(uuid.uuid4()),
                            home_team=home,
                            away_team=away,
                            league=league,
                            market="1x2",
                            selection="away",
                            odds=odd_away,
                            bookmaker=self.name,
                            timestamp=datetime.utcnow().isoformat() + "Z",
                        )
                    )

                except Exception:
                    continue

        except Exception as e:
            print(f"[StakeScraper] erro: {e}")

        return out
