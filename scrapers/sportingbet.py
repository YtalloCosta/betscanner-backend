import uuid
import aiohttp
from datetime import datetime
from typing import List

from models.odds import Odds
from scrapers.base import BaseScraper

from utils.normalize import (
    clean_team_name,
    clean_market_name,
    clean_selection_name,
    clean_league_name
)


class SportingbetScraper(BaseScraper):
    name = "sportingbet"

    API_URL = "https://sports.sportingbet.com/api/sportsbook/events"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        results: List[Odds] = []

        params = {
            "sports": "futebol",
            "template": "simple",
            "days_ahead": days_ahead
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(self.API_URL, params=params) as resp:
                if resp.status != 200:
                    print(f"[sportingbet] HTTP {resp.status}")
                    return []

                try:
                    data = await resp.json()
                except Exception as e:
                    print("[sportingbet] JSON error:", e)
                    return []

        events = data.get("events", [])
        for ev in events:
            try:
                home = clean_team_name(ev["home"])
                away = clean_team_name(ev["away"])
                league = clean_league_name(ev.get("league", ""))

                start_time = ev.get("startTime")
                timestamp = datetime.utcnow().isoformat()

                event_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{home}-{away}-{start_time}"))

                markets = ev.get("markets", [])

                for m in markets:
                    market_name = clean_market_name(m.get("name", ""))

                    for sel in m.get("selections", []):
                        selection = clean_selection_name(sel["name"])
                        price = float(sel["odds"])

                        odd_obj = Odds(
                            event_id=event_id,
                            home_team=home,
                            away_team=away,
                            league=league,
                            sport="soccer",
                            market=market_name,
                            selection=selection,
                            odds=price,
                            bookmaker="sportingbet",
                            timestamp=timestamp,
                            start_time=start_time,
                        )

                        results.append(odd_obj)

            except Exception as e:
                print("[sportingbet] parse error:", e)
                continue

        return results
