import aiohttp
import uuid
from datetime import datetime
from typing import List
from playwright.async_api import async_playwright

from scrapers.base import BaseScraper
from models.odds import Odds
from utils.normalize import (
    clean_team_name,
    clean_league_name,
    clean_market_name,
    clean_selection_name
)


class BetanoScraper(BaseScraper):
    name = "betano"
    PAGE_URL = "https://br.betano.com/sport/futebol/"
    API_URL = "https://br.betano.com/api/sportsbook/"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        out: List[Odds] = []

        # 1. PLAYWRIGHT → pegar token
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            page = await browser.new_page()
            await page.goto(self.PAGE_URL, timeout=60000)
            await page.wait_for_timeout(3000)

            token = await page.evaluate("""
                () => window.localStorage.getItem('apiSportsbookAccessToken')
            """)

            await browser.close()

        if not token:
            print("[Betano] ERRO: token não encontrado")
            return out

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "operationName": "Events",
            "variables": { "sportId": 1, "limit": 60, "skip": 0 },
            "query": """
            query Events($sportId: Int!, $limit: Int!, $skip: Int!) {
                events(sportId: $sportId, limit: $limit, skip: $skip) {
                    id
                    name
                    competition { name }
                    participants { name position }
                    markets {
                        key
                        selections { name price }
                    }
                }
            }
            """
        }

        # 2. API → eventos reais
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.API_URL, json=payload, headers=headers) as resp:
                    data = await resp.json()
        except Exception as e:
            print("[Betano API ERROR]", e)
            return out

        events = data.get("data", {}).get("events", [])
        timestamp = datetime.utcnow().isoformat() + "Z"

        # 3. Processar eventos
        for ev in events:
            try:
                league = clean_league_name(ev["competition"]["name"])

                home = clean_team_name(
                    next(p["name"] for p in ev["participants"] if p["position"] == "home")
                )
                away = clean_team_name(
                    next(p["name"] for p in ev["participants"] if p["position"] == "away")
                )

                event_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{home}-{away}-{league}"))

                for m in ev.get("markets", []):
                    market_key = clean_market_name(m["key"])

                    for sel in m.get("selections", []):
                        selection = clean_selection_name(sel["name"])
                        price = float(sel["price"])

                        out.append(Odds(
                            event_id=event_id,
                            home_team=home,
                            away_team=away,
                            league=league,
                            sport="soccer",
                            market=market_key,
                            selection=selection,
                            odds=price,
                            bookmaker=self.name,
                            timestamp=timestamp,
                            start_time=None,
                        ))

            except Exception:
                continue

        return out
