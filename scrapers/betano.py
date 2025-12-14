import aiohttp
import uuid
import json
from datetime import datetime
from typing import List
from scrapers.base import BaseScraper
from models.odds import Odds
from playwright.async_api import async_playwright

from utils.normalize import (
    clean_team_name,
    clean_league_name,
    clean_market_name,
    clean_selection_name,
)


class BetanoScraper(BaseScraper):
    name = "betano"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        out: List[Odds] = []

        PAGE_URL = "https://br.betano.com/sport/futebol/"
        API_URL = "https://br.betano.com/api/sportsbook/"

        # ================================
        # 1) Captura token via Playwright
        # ================================
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            page = await browser.new_page()

            await page.goto(PAGE_URL, timeout=60000)
            await page.wait_for_timeout(3000)

            token = await page.evaluate(
                "() => window.localStorage.getItem('apiSportsbookAccessToken')"
            )

            await browser.close()

        if not token:
            print("[BETANO] TOKEN NÃO ENCONTRADO")
            return out

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # ================================
        # 2) Query GraphQL real da Betano
        # ================================
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
            """,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, json=payload, headers=headers, timeout=20) as resp:
                    data = await resp.json()
        except Exception as e:
            print(f"[BETANO API ERROR] {e}")
            return out

        events = data.get("data", {}).get("events", [])

        # ===========================================
        # 3) Processamento dos eventos corretamente
        # ===========================================
        for ev in events:
            try:
                league = clean_league_name(ev["competition"]["name"])
                start_time = ev.get("startTime")
                timestamp = datetime.utcnow().isoformat() + "Z"

                home = clean_team_name(
                    next(p["name"] for p in ev["participants"] if p["position"] == "home")
                )
                away = clean_team_name(
                    next(p["name"] for p in ev["participants"] if p["position"] == "away")
                )

                event_uid = str(uuid.uuid4())  # UM ÚNICO event_id POR EVENTO

                markets = ev.get("markets", [])

                for m in markets:
                    key = m["key"]
                    selections = m.get("selections", [])

                    # --------------------------------------------------
                    # 1) MERCADO 1x2 → chave correta: match_result
                    # --------------------------------------------------
                    if key == "match_result":
                        for sel in selections:
                            sel_clean = clean_selection_name(sel["name"])
                            out.append(
                                Odds(
                                    event_id=event_uid,
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    market="1x2",
                                    selection=sel_clean,
                                    odds=float(sel["price"]),
                                    bookmaker=self.name,
                                    timestamp=timestamp,
                                    start_time=start_time,
                                )
                            )

                    # --------------------------------------------------
                    # 2) BTTS
                    # --------------------------------------------------
                    if key == "both_teams_to_score":
                        for sel in selections:
                            sel_clean = clean_selection_name(sel["name"])
                            out.append(
                                Odds(
                                    event_id=event_uid,
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    market="btts",
                                    selection=sel_clean,  # yes/no
                                    odds=float(sel["price"]),
                                    bookmaker=self.name,
                                    timestamp=timestamp,
                                    start_time=start_time,
                                )
                            )

                    # --------------------------------------------------
                    # 3) Over/Under — Betano usa 'totals'
                    # --------------------------------------------------
                    if key == "totals":
                        for sel in selections:
                            out.append(
                                Odds(
                                    event_id=event_uid,
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    market="over_under",
                                    selection=sel["name"].lower(),  # ex: over 2.5
                                    odds=float(sel["price"]),
                                    bookmaker=self.name,
                                    timestamp=timestamp,
                                    start_time=start_time,
                                )
                            )

                    # --------------------------------------------------
                    # 4) Handicap — mantido apenas o asiático
                    # --------------------------------------------------
                    if key == "asian_handicap":
                        for sel in selections:
                            out.append(
                                Odds(
                                    event_id=event_uid,
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    market="ah",
                                    selection=sel["name"].lower(),  # ex: home -1.5
                                    odds=float(sel["price"]),
                                    bookmaker=self.name,
                                    timestamp=timestamp,
                                    start_time=start_time,
                                )
                            )

            except Exception as e:
                print(f"[BETANO PARSE ERROR] {e}")
                continue

        return out
