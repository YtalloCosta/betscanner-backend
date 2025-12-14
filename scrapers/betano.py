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


class BetanoScraper(BaseScraper):
    name = "betano"

    PAGE_URL = "https://br.betano.com/sport/futebol/"
    API_URL = "https://br.betano.com/api/sportsbook/"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        results: List[Odds] = []

        # ======================================================
        # 1) COLETAR TOKEN VIA PLAYWRIGHT
        # ======================================================
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            page = await browser.new_page()

            await page.goto(self.PAGE_URL, timeout=60000)
            await page.wait_for_timeout(3000)

            token = await page.evaluate(
                "() => window.localStorage.getItem('apiSportsbookAccessToken')"
            )

            await browser.close()

        if not token:
            print("[Betano] Token não encontrado")
            return results

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # ======================================================
        # 2) QUERY GRAPHQL REAL DA BETANO
        # ======================================================
        payload = {
            "operationName": "Events",
            "variables": {"sportId": 1, "limit": 200, "skip": 0},
            "query": """
            query Events($sportId: Int!, $limit: Int!, $skip: Int!) {
              events(sportId: $sportId, limit: $limit, skip: $skip) {
                id
                name
                startTime
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

        # ======================================================
        # 3) BUSCAR EVENTOS
        # ======================================================
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.API_URL, headers=headers, json=payload, timeout=20) as resp:
                    data = await resp.json()
        except Exception as e:
            print("[Betano API Error]", e)
            return results

        events = data.get("data", {}).get("events", [])

        # ======================================================
        # 4) PROCESSAR EVENTOS
        # ======================================================
        for ev in events:
            try:
                league = clean_league_name(ev["competition"]["name"])
                start_time = ev.get("startTime")

                home = clean_team_name(
                    next(p["name"] for p in ev["participants"] if p["position"] == "home")
                )
                away = clean_team_name(
                    next(p["name"] for p in ev["participants"] if p["position"] == "away")
                )

                timestamp = datetime.utcnow().isoformat() + "Z"
                event_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{home}-{away}-{start_time}"))

                markets = ev.get("markets", [])

                # PARA IDENTIFICAR MERCADOS PRINCIPAIS
                found_over_under = False
                found_asian = False

                for m in markets:
                    key = m["key"]
                    selections = m.get("selections", [])

                    # ================================
                    # 1) MERCADO 1X2
                    # ================================
                    if key == "match_result":
                        for sel in selections:
                            selection = clean_selection_name(sel["name"])
                            results.append(
                                Odds(
                                    event_id=event_id,
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    sport="soccer",
                                    market="1x2",
                                    selection=selection,
                                    odds=float(sel["price"]),
                                    bookmaker=self.name,
                                    timestamp=timestamp,
                                    start_time=start_time,
                                )
                            )

                    # ================================
                    # 2) DUPLA CHANCE
                    # ================================
                    if key == "double_chance":
                        for sel in selections:
                            selection = sel["name"].upper()  # 1X / X2 / 12
                            results.append(
                                Odds(
                                    event_id=event_id,
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    sport="soccer",
                                    market="double_chance",
                                    selection=selection,
                                    odds=float(sel["price"]),
                                    bookmaker=self.name,
                                    timestamp=timestamp,
                                    start_time=start_time,
                                )
                            )

                    # ================================
                    # 3) OVER/UNDER PRINCIPAL
                    # ================================
                    if key == "totals" and not found_over_under:
                        # Betano sempre lista a linha principal primeiro → usamos só a primeira
                        sel = selections[0]
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
                        found_over_under = True

                    # ================================
                    # 4) BTTS
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
                    # 5) AH PRINCIPAL
                    # ================================
                    if key == "asian_handicap" and not found_asian:
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
                        found_asian = True

            except Exception as e:
                print("[Betano Parse Error]", e)
                continue

        return results
