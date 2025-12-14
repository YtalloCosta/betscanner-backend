import aiohttp
import uuid
from datetime import datetime
from typing import List

from playwright.async_api import async_playwright
from scrapers.base import BaseScraper
from models.odds import Odds


class KTOScraper(BaseScraper):
    name = "kto"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        out: List[Odds] = []

        PAGE_URL = "https://kto.com/sports/futebol/"
        
        # API OFICIAL DA KTO
        API_URL = "https://kto.com/api/sportsbook/events"

        # --------------------------------------------------
        # 1) COLETAR TOKEN DA KTO VIA PLAYWRIGHT
        # --------------------------------------------------
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            page = await browser.new_page()

            await page.goto(PAGE_URL, timeout=60000)
            await page.wait_for_timeout(3000)

            token = await page.evaluate("""
                () => window.localStorage.getItem('authToken')
            """)

            await browser.close()

        if not token:
            print("[KTO] ERRO: authToken não encontrado.")
            return out

        # --------------------------------------------------
        # 2) REQUISIÇÃO À API REAL DA KTO
        # --------------------------------------------------
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

        payload = {
            "sportIds": [1],  # 1 = Futebol
            "limit": 50,
            "offset": 0,
            "includeMarkets": True,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, headers=headers, json=payload, timeout=20) as resp:
                    data = await resp.json()
        except Exception as e:
            print(f"[KTO API ERROR] {e}")
            return out

        events = data.get("events", [])

        # --------------------------------------------------
        # 3) PROCESSAR EVENTOS
        # --------------------------------------------------
        for ev in events:
            try:
                league = ev.get("competition", {}).get("name", "KTO")

                participants = ev.get("participants", [])
                home = next((p["name"] for p in participants if p["position"] == "home"), None)
                away = next((p["name"] for p in participants if p["position"] == "away"), None)

                if not home or not away:
                    continue

                markets = ev.get("markets", [])

                for m in markets:
                    key = m.get("key")
                    selections = m.get("selections", [])

                    # --------------------------
                    # MERCADO 1X2
                    # --------------------------
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

                    # --------------------------
                    # DUPLA CHANCE
                    # --------------------------
                    if key == "double_chance":
                        for sel in selections:
                            out.append(Odds(
                                event_id=str(uuid.uuid4()),
                                home_team=home,
                                away_team=away,
                                league=league,
                                market="double_chance",
                                selection=sel["name"],  # "1X", "X2", "12"
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=datetime.utcnow().isoformat() + "Z",
                            ))

                    # --------------------------
                    # OVER / UNDER
                    # --------------------------
                    if key == "totals":
                        for sel in selections:
                            out.append(Odds(
                                event_id=str(uuid.uuid4()),
                                home_team=home,
                                away_team=away,
                                league=league,
                                market="over_under",
                                selection=sel["name"],  # ex: "over 2.5"
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=datetime.utcnow().isoformat() + "Z",
                            ))

                    # --------------------------
                    # AMBAS MARCAM
                    # --------------------------
                    if key == "both_teams_to_score":
                        for sel in selections:
                            out.append(Odds(
                                event_id=str(uuid.uuid4()),
                                home_team=home,
                                away_team=away,
                                league=league,
                                market="btts",
                                selection=sel["name"],  # yes/no
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=datetime.utcnow().isoformat() + "Z"
                            ))

                    # --------------------------
                    # HANDICAP ASIÁTICO
                    # --------------------------
                    if key == "asian_handicap":
                        for sel in selections:
                            out.append(Odds(
                                event_id=str(uuid.uuid4()),
                                home_team=home,
                                away_team=away,
                                league=league,
                                market="asian_handicap",
                                selection=sel["name"],  # ex: "home -1.5"
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=datetime.utcnow().isoformat() + "Z"
                            ))

            except Exception:
                continue

        return out
