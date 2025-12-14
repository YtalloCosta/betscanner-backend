import uuid
import aiohttp
from datetime import datetime
from typing import List
from playwright.async_api import async_playwright

from scrapers.base import BaseScraper
from models.odds import Odds

from utils.normalize import (
    clean_team_name,
    clean_league_name,
    clean_selection_name
)


class SportingbetScraper(BaseScraper):
    name = "sportingbet"

    PAGE_URL = "https://sports.sportingbet.com/pt-br/sports/futebol-4"
    API_URL = "https://sports.sportingbet.com/api/sportsbook/events"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        results: List[Odds] = []

        # ============================================================
        # 1) CAPTURAR TOKEN VIA PLAYWRIGHT
        # ============================================================
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox"]
                )
                page = await browser.new_page()

                await page.goto(self.PAGE_URL, timeout=60000)
                await page.wait_for_timeout(3000)

                token = await page.evaluate(
                    "() => window.localStorage.getItem('auth.access_token')"
                )

                await browser.close()

        except Exception as e:
            print("[Sportingbet] TOKEN ERROR:", e)
            return results

        if not token:
            print("[Sportingbet] Token não encontrado")
            return results

        # ============================================================
        # 2) API REQUEST REAL
        # ============================================================
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {
            "sportIds": [4],               # Futebol
            "marketLimit": 200,
            "count": 200,
            "offset": 0,
            "includeMarkets": True,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.API_URL, headers=headers, json=payload, timeout=20) as resp:
                    data = await resp.json()
        except Exception as e:
            print("[Sportingbet API] error:", e)
            return results

        events = data.get("events", [])

        # ============================================================
        # 3) PROCESSAR EVENTOS
        # ============================================================
        for ev in events:
            try:
                league = clean_league_name(ev.get("competition", {}).get("name", ""))

                home = clean_team_name(
                    next((p["name"] for p in ev.get("participants", []) if p["position"] == "home"), None)
                )
                away = clean_team_name(
                    next((p["name"] for p in ev.get("participants", []) if p["position"] == "away"), None)
                )

                if not home or not away:
                    continue

                start_time = ev.get("startTime")

                # event_id determinístico por evento + casa
                event_id = str(uuid.uuid5(
                    uuid.NAMESPACE_DNS,
                    f"{home}-{away}-{start_time}-sportingbet"
                ))

                markets = ev.get("markets", [])
                timestamp = datetime.utcnow().isoformat() + "Z"

                # ============================================================
                # 1X2
                # ============================================================
                m_1x2 = next((m for m in markets if m["key"] == "match_result"), None)
                if m_1x2:
                    for sel in m_1x2.get("selections", []):
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

                # ============================================================
                # DUPLA CHANCE
                # ============================================================
                m_dc = next((m for m in markets if m["key"] == "double_chance"), None)
                if m_dc:
                    for sel in m_dc.get("selections", []):
                        results.append(
                            Odds(
                                event_id=event_id,
                                home_team=home,
                                away_team=away,
                                league=league,
                                sport="soccer",
                                market="double_chance",
                                selection=sel["name"],
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=timestamp,
                                start_time=start_time,
                            )
                        )

                # ============================================================
                # OVER / UNDER
                # ============================================================
                m_ou = next((m for m in markets if m["key"] == "totals"), None)
                if m_ou:
                    for sel in m_ou.get("selections", []):
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

                # ============================================================
                # BTTS
                # ============================================================
                m_btts = next((m for m in markets if m["key"] == "both_teams_to_score"), None)
                if m_btts:
                    for sel in m_btts.get("selections", []):
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

                # ============================================================
                # ASIAN HANDICAP
                # ============================================================
                m_ah = next((m for m in markets if m["key"] == "asian_handicap"), None)
                if m_ah:
                    for sel in m_ah.get("selections", []):
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

            except Exception as e:
                print("[Sportingbet] parse error:", e)
                continue

        return results
