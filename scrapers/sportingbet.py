import aiohttp
import uuid
import json
from datetime import datetime
from typing import List

from scrapers.base import BaseScraper
from models.odds import Odds
from playwright.async_api import async_playwright


class SportingBetScraper(BaseScraper):
    name = "sportingbet"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        out: List[Odds] = []

        PAGE_URL = "https://sports.sportingbet.com/pt-br/sports/futebol-4"
        API_URL = "https://sports.sportingbet.com/api/sportsbook/events"

        # 1) Capturar token via Playwright
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )

            page = await browser.new_page()
            await page.goto(PAGE_URL, timeout=60000)
            await page.wait_for_timeout(4000)

            token = await page.evaluate("""
                () => window.localStorage.getItem('auth.access_token')
            """)

            await browser.close()

        if not token:
            print("[Sportingbet] Token não encontrado")
            return out

        # 2) Chamada da API real
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "sportIds": [4],
            "marketLimit": 100,
            "count": 50,
            "offset": 0,
            "includeMarkets": True
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, json=payload, headers=headers, timeout=20) as resp:
                    data = await resp.json()
        except Exception as e:
            print(f"[Sportingbet API error] {e}")
            return out

        events = data.get("events", [])

        # 3) Processar mercados
        for ev in events:
            try:
                league = ev.get("competition", {}).get("name", "Sportingbet")

                home = ev["participants"][0]["name"]
                away = ev["participants"][1]["name"]

                markets = ev.get("markets", [])

                for m in markets:
                    key = m.get("key", "")
                    selections = m.get("selections", [])

                    # Match Odds
                    if key == "match_result":
                        for sel in selections:
                            out.append(Odds(
                                event_id=str(uuid.uuid4()),
                                home_team=home,
                                away_team=away,
                                league=league,
                                market="1x2",
                                selection=sel["name"].lower(),
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=datetime.utcnow().isoformat() + "Z",
                            ))

                    # Dupla Chance
                    if key == "double_chance":
                        for sel in selections:
                            out.append(Odds(
                                event_id=str(uuid.uuid4()),
                                home_team=home,
                                away_team=away,
                                league=league,
                                market="double_chance",
                                selection=sel["name"],
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=datetime.utcnow().isoformat() + "Z",
                            ))

                    # Over/Under
                    if key == "totals":
                        for sel in selections:
                            out.append(Odds(
                                event_id=str(uuid.uuid4()),
                                home_team=home,
                                away_team=away,
                                league=league,
                                market="over_under",
                                selection=sel["name"],
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=datetime.utcnow().isoformat() + "Z",
                            ))

                    # BTTS
                    if key == "both_teams_to_score":
                        for sel in selections:
                            out.append(Odds(
                                event_id=str(uuid.uuid4()),
                                home_team=home,
                                away_team=away,
                                league=league,
                                market="btts",
                                selection=sel["name"],
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=datetime.utcnow().isoformat() + "Z",
                            ))

                    # Handicap Asiático
                    if key == "asian_handicap":
                        for sel in selections:
                            out.append(Odds(
                                event_id=str(uuid.uuid4()),
                                home_team=home,
                                away_team=away,
                                league=league,
                                market="asian_handicap",
                                selection=sel["name"],
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=datetime.utcnow().isoformat() + "Z",
                            ))

            except Exception:
                continue

        return out
