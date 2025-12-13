import httpx
from datetime import datetime
from typing import List
from models.odds import Odds
from scrapers.base import BaseScraper


PINNACLE_API = "https://guest.api.arcadia.pinnacle.com/0.1/sports/soccer/matches/live"


class PinnacleScraper(BaseScraper):
    name = "pinnacle"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.get(PINNACLE_API)
                data = response.json()
            except Exception as e:
                print("Erro ao acessar API da Pinnacle:", e)
                return []

        out: List[Odds] = []

        for event in data:
            try:
                home = event["home"]
                away = event["away"]

                markets = event.get("markets", [])
                h2h = next((m for m in markets if m["key"] == "h2h"), None)

                if not h2h:
                    continue

                prices = h2h.get("prices", [])
                if len(prices) < 2:
                    continue

                odds_home = float(prices[0]["price"])
                odds_away = float(prices[1]["price"])

                out.append(Odds(
                    event_id=str(event["id"]),
                    home_team=home,
                    away_team=away,
                    league=event.get("league", {}).get("name", "Unknown League"),
                    market="1x2",
                    selection="home",
                    odds=odds_home,
                    bookmaker=self.name,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                ))

                out.append(Odds(
                    event_id=str(event["id"]),
                    home_team=home,
                    away_team=away,
                    league=event.get("league", {}).get("name", "Unknown League"),
                    market="1x2",
                    selection="away",
                    odds=odds_away,
                    bookmaker=self.name,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                ))

            except Exception:
                continue

        return out
