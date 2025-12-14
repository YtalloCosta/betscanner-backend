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

    async def _get_token(self) -> str | None:
        """
        Captura o token real da KTO usando localStorage.
        A KTO muda esse token às vezes, então fazemos fallback inteligente.
        """
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            page = await browser.new_page()

            await page.goto(self.PAGE_URL, timeout=60000)
            await page.wait_for_timeout(3000)

            token = await page.evaluate(
                """
                () => (
                    window.localStorage.getItem('auth.access_token')
                    || window.localStorage.getItem('authToken')
                    || window.localStorage.getItem('token')
                )
                """
            )

            await browser.close()

        return token

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        out: List[Odds] = []

        # ===============================
        # 1) Capturar token real
        # ===============================
        token = await self._get_token()
        if not token:
            print("[KTO] ERRO: Token não encontrado.")
            return out

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

        payload = {
            "sportIds": [1],   # 1 = Futebol
            "limit": 200,
            "offset": 0,
            "includeMarkets": True,
        }

        # ===============================
        # 2) Chamada à API real
        # ===============================
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.API_URL, json=payload, headers=headers, timeout=30
                ) as resp:
                    data = await resp.json()
        except Exception as e:
            print(f"[KTO API ERROR] {e}")
            return out

        events = data.get("events", [])

        # ===============================
        # 3) Processar eventos
        # ===============================
        for ev in events:
            try:
                league = clean_league_name(
                    ev.get("competition", {}).get("name", "KTO")
                )

                start_time = ev.get("startTime")
                timestamp = datetime.utcnow().isoformat() + "Z"

                participants = ev.get("participants", [])

                home = clean_team_name(
                    next((p["name"] for p in participants if p["position"] == "home"), None)
                )
                away = clean_team_name(
                    next((p["name"] for p in participants if p["position"] == "away"), None)
                )

                if not home or not away:
                    continue

                # UM único event_id por partida
                event_uid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"kto-{home}-{away}-{start_time}"))

                markets = ev.get("markets", [])

                for m in markets:
                    key = m.get("key", "")
                    selections = m.get("selections", [])

                    # ------------------------------------
                    # MERCADO 1x2
                    # ------------------------------------
                    if key == "match_result":
                        for sel in selections:
                            selection = clean_selection_name(sel["name"])

                            out.append(
                                Odds(
                                    event_id=event_uid,
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

                    # ------------------------------------
                    # DUPLA CHANCE
                    # ------------------------------------
                    if key == "double_chance":
                        for sel in selections:
                            selection = clean_selection_name(sel["name"])

                            out.append(
                                Odds(
                                    event_id=event_uid,
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

                    # ------------------------------------
                    # OVER / UNDER
                    # ------------------------------------
                    if key == "totals":
                        for sel in selections:
                            selection = clean_selection_name(sel["name"])

                            out.append(
                                Odds(
                                    event_id=event_uid,
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    sport="soccer",
                                    market="over_under",
                                    selection=selection,
                                    odds=float(sel["price"]),
                                    bookmaker=self.name,
                                    timestamp=timestamp,
                                    start_time=start_time,
                                )
                            )

                    # ------------------------------------
                    # BTTS
                    # ------------------------------------
                    if key == "both_teams_to_score":
                        for sel in selections:
                            selection = clean_selection_name(sel["name"])

                            out.append(
                                Odds(
                                    event_id=event_uid,
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    sport="soccer",
                                    market="btts",
                                    selection=selection,
                                    odds=float(sel["price"]),
                                    bookmaker=self.name,
                                    timestamp=timestamp,
                                    start_time=start_time,
                                )
                            )

                    # ------------------------------------
                    # ASIAN HANDICAP
                    # ------------------------------------
                    if key == "asian_handicap":
                        for sel in selections:
                            selection = clean_selection_name(sel["name"])

                            out.append(
                                Odds(
                                    event_id=event_uid,
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    sport="soccer",
                                    market="ah",
                                    selection=selection,
                                    odds=float(sel["price"]),
                                    bookmaker=self.name,
                                    timestamp=timestamp,
                                    start_time=start_time,
                                )
                            )

            except Exception as e:
                print(f"[KTO PARSE ERROR] {e}")
                continue

        return out
