import uuid
import aiohttp
from datetime import datetime
from typing import List
from playwright.async_api import async_playwright

from scrapers.base import BaseScraper
from models.odds import Odds

from utils.normalize import (
    clean_team_name,
    clean_market_name,
    clean_selection_name,
    clean_league_name
)


class SportingbetScraper(BaseScraper):
    name = "sportingbet"

    PAGE_URL = "https://sports.sportingbet.com/pt-br/sports/futebol-4"
    API_URL = "https://sports.sportingbet.com/api/sportsbook/events"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        results: List[Odds] = []

        # ============================================================
        # 1) CAPTURAR TOKEN REAL DA SPORTINGBET PELO PLAYWRIGHT
        # ============================================================
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox"]
                )
                page = await browser.new_page()

                await page.goto(self.PAGE_URL, timeout=60000)
                await page.wait_for_timeout(3500)

                token = await page.evaluate(
                    "() => window.localStorage.getItem('auth.access_token')"
                )

                await browser.close()

        except Exception as e:
            print("[Sportingbet] Falha ao capturar token:", e)
            return results

        if not token:
            print("[Sportingbet] Token não encontrado!")
            return results

        # ============================================================
        # 2) FAZER REQUEST REAL PARA A API DA SPORTINGBET
        # ============================================================
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {
            "sportIds": [4],  # futebol
            "marketLimit": 200,
            "count": 100,
            "offset": 0,
            "includeMarkets": True,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.API_URL, json=payload, headers=headers, timeout=20) as resp:
                    data = await resp.json()
        except Exception as e:
            print("[Sportingbet API] erro:", e)
            return results

        events = data.get("events", [])

        # ============================================================
        # 3) PROCESSAR EVENTOS
        # ============================================================
        for ev in events:
            try:
                league = clean_league_name(ev.get("competition", {}).get("name", ""))

                participants = ev.get("participants", [])
                home = next((p["name"] for p in participants if p["position"] == "home"), None)
                away = next((p["name"] for p in participants if p["position"] == "away"), None)

                if not home or not away:
                    continue

                home = clean_team_name(home)
                away = clean_team_name(away)

                start_time = ev.get("startTime")

                # EVENT ID ESTÁVEL
                event_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{home}-{away}-{start_time}"))

                markets = ev.get("markets", [])

                # ====================================================
                # 4) PROCESSAR CADA MERCADO
                # ====================================================
                for m in markets:
                    market_key = m.get("key")
                    selections = m.get("selections", [])

                    # ------------------------ 1X2 ------------------------
                    if market_key == "match_result":
                        for sel in selections:
                            results.append(Odds(
                                event_id=event_id,
                                home_team=home,
                                away_team=away,
                                league=league,
                                sport="soccer",
                                market="1x2",
                                selection=clean_selection_name(sel["name"]),
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=datetime.utcnow().isoformat() + "Z",
                                start_time=start_time
                            ))

                    # ------------------ DUPLA CHANCE ---------------------
                    if market_key == "double_chance":
                        for sel in selections:
                            results.append(Odds(
                                event_id=event_id,
                                home_team=home,
                                away_team=away,
                                league=league,
                                sport="soccer",
                                market="double_chance",
                                selection=sel["name"],  # já vem padronizado: 1X / 12 / X2
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=datetime.utcnow().isoformat() + "Z",
                                start_time=start_time
                            ))

                    # ------------------- OVER / UNDER ---------------------
                    if market_key == "totals":
                        for sel in selections:
                            results.append(Odds(
                                event_id=event_id,
                                home_team=home,
                                away_team=away,
                                league=league,
                                sport="soccer",
                                market="over_under",
                                selection=clean_selection_name(sel["name"]),
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=datetime.utcnow().isoformat() + "Z",
                                start_time=start_time
                            ))

                    # ------------------- AMBAS MARCAM ---------------------
                    if market_key == "both_teams_to_score":
                        for sel in selections:
                            results.append(Odds(
                                event_id=event_id,
                                home_team=home,
                                away_team=away,
                                league=league,
                                sport="soccer",
                                market="btts",
                                selection=clean_selection_name(sel["name"]),
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=datetime.utcnow().isoformat() + "Z",
                                start_time=start_time
                            ))

                    # ---------------- HANDICAP ASIÁTICO --------------------
                    if market_key == "asian_handicap":
                        for sel in selections:
                            results.append(Odds(
                                event_id=event_id,
                                home_team=home,
                                away_team=away,
                                league=league,
                                sport="soccer",
                                market="asian_handicap",
                                selection=sel["name"],
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=datetime.utcnow().isoformat() + "Z",
                                start_time=start_time
                            ))

            except Exception as e:
                print("[Sportingbet] erro de parsing:", e)
                continue

        return results
