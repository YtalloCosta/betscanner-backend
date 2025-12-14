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
    clean_selection_name,
)


class KTOScraper(BaseScraper):
    name = "kto"

    PAGE_URL = "https://kto.com/sports/futebol/"
    API_URL = "https://kto.com/api/sportsbook/events"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        results: List[Odds] = []

        # ======================================================
        # 1) CAPTURAR authToken (identidade) via Playwright
        # ======================================================
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            page = await browser.new_page()

            await page.goto(self.PAGE_URL, timeout=60000)
            await page.wait_for_timeout(3000)

            token = await page.evaluate(
                "() => window.localStorage.getItem('authToken')"
            )

            await browser.close()

        if not token:
            print("[KTO] Token não encontrado.")
            return results

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {
            "sportIds": [1],  # Futebol
            "limit": 200,
            "offset": 0,
            "includeMarkets": True,
        }

        # ======================================================
        # 2) CHAMADA À API REAL DA KTO
        # ======================================================
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.API_URL, json=payload, headers=headers, timeout=20
                ) as resp:
                    data = await resp.json()
        except Exception as e:
            print("[KTO API ERROR]", e)
            return results

        events = data.get("events", [])

        # ======================================================
        # 3) PROCESSAR EVENTOS
        # ======================================================
        for ev in events:
            try:
                league = clean_league_name(ev.get("competition", {}).get("name", "KTO"))

                participants = ev.get("participants", [])
                home = clean_team_name(
                    next((p["name"] for p in participants if p["position"] == "home"), None)
                )
                away = clean_team_name(
                    next((p["name"] for p in participants if p["position"] == "away"), None)
                )

                if not home or not away:
                    continue

                start_time = ev.get("startTime")
                timestamp = datetime.utcnow().isoformat() + "Z"

                event_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{home}-{away}-{start_time}"))

                markets = ev.get("markets", [])

                found_ou = False
                found_ah = False

                for m in markets:
                    key = m.get("key", "").lower()
                    selections = m.get("selections", [])

                    # ================================
                    # 1) 1X2 — match_result
                    # ================================
                    if key == "match_result":
                        for sel in selections:
                            results.append(
                                Odds(
                                    event_id=event_id,
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    sport="soccer",
                                    market="1x2",
                                    selection=clean_selection_name(sel["name"]),
                                    odds=float(sel["price"]),
                                    bookmaker=self.name,
                                    timestamp=timestamp,
                                    start_time=start_time,
                                )
                            )

                    # ================================
                    # 2) DUPLA CHANCE — double_chance
                    # ================================
                    if key == "double_chance":
                        for sel in selections:
                            results.append(
                                Odds(
                                    event_id=event_id,
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    sport="soccer",
                                    market="double_chance",
                                    selection=sel["name"].upper(),  # 1X / X2 / 12
                                    odds=float(sel["price"]),
                                    bookmaker=self.name,
                                    timestamp=timestamp,
                                    start_time=start_time,
                                )
                            )

                    # ================================
                    # 3) OVER/UNDER — totals (pega só o principal)
                    # ================================
                    if key == "totals" and not found_ou:
                        sel = selections[0]  # principal
                        results.append(
                            Odds(
                                event_id=event_id,
                                home_team=home,
                                away_team=away,
                                league=league,
                                sport="soccer",
                                market="over_under",
                                selection=clean_selection_name(sel["name"]),
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=timestamp,
                                start_time=start_time,
                            )
                        )
                        found_ou = True

                    # ================================
                    # 4) BTTS — both_teams_to_score
                    # ================================
                    if key == "both_teams_to_score":
                        for sel in selections:
                            results.append(
                                Odds(
                                    event_id=event_id,
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    sport="soccer",
                                    market="btts",
                                    selection=clean_selection_name(sel["name"]),
                                    odds=float(sel["price"]),
                                    bookmaker=self.name,
                                    timestamp=timestamp,
                                    start_time=start_time,
                                )
                            )

                    # ================================
                    # 5) ASIAN HANDICAP — asian_handicap (pega só o principal)
                    # ================================
                    if key == "asian_handicap" and not found_ah:
                        sel = selections[0]
                        results.append(
                            Odds(
                                event_id=event_id,
                                home_team=home,
                                away_team=away,
                                league=league,
                                sport="soccer",
                                market="asian_handicap",
                                selection=clean_selection_name(sel["name"]),
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=timestamp,
                                start_time=start_time,
                            )
                        )
                        found_ah = True

            except Exception as e:
                print("[KTO PARSE ERROR]", e)
                continue

        return results
