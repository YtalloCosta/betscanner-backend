import aiohttp
import uuid
import json
from datetime import datetime
from typing import List
from scrapers.base import BaseScraper
from models.odds import Odds
from playwright.async_api import async_playwright


class BetanoScraper(BaseScraper):
    name = "betano"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        out: List[Odds] = []

        # URL da página (apenas para pegar o token)
        PAGE_URL = "https://br.betano.com/sport/futebol/"

        # Endpoint real da API da Betano (GraphQL)
        API_URL = "https://br.betano.com/api/sportsbook/"

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            page = await browser.new_page()

            # 1) Abre a página para capturar token
            await page.goto(PAGE_URL, timeout=60000)
            await page.wait_for_timeout(4000)

            # 2) Token da API usado pelo site (autorização)
            token = await page.evaluate("""
                () => window.localStorage.getItem('apiSportsbookAccessToken')
            """)

            if not token:
                print("[Betano] Token não encontrado")
                await browser.close()
                return out

            # 3) Fecha Playwright cedo — token já foi obtido
            await browser.close()

        # 4) Agora, chamamos a API diretamente, usando o token
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # GraphQL query padrão usada pela Betano para listar eventos
        payload = {
            "operationName": "Events",
            "variables": {
                "sportId": 1,
                "limit": 50,
                "skip": 0
            },
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

        # 5) Chama a API real da Betano
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, json=payload, headers=headers, timeout=20) as resp:
                    data = await resp.json()
        except Exception as e:
            print(f"[Betano API error] {e}")
            return out

        events = data.get("data", {}).get("events", [])

        for ev in events:
            try:
                league = ev["competition"]["name"]

                # Times
                home = next(p["name"] for p in ev["participants"] if p["position"] == "home")
                away = next(p["name"] for p in ev["participants"] if p["position"] == "away")

                # Mercados
                markets = ev.get("markets", [])

                for m in markets:
                    key = m["key"]
                    selections = m.get("selections", [])

                    # =========================
                    # 1) 1X2
                    # =========================
                    if key == "match_result":
                        for sel in selections:
                            out.append(Odds(
                                event_id=str(uuid.uuid4()),
                                home_team=home,
                                away_team=away,
                                league=league,
                                market="1x2",
                                selection=sel["name"].lower(),  # home / draw / away
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=datetime.utcnow().isoformat() + "Z",
                            ))

                    # =========================
                    # 2) Dupla Chance
                    # =========================
                    if key == "double_chance":
                        for sel in selections:
                            out.append(Odds(
                                event_id=str(uuid.uuid4()),
                                home_team=home,
                                away_team=away,
                                league=league,
                                market="double_chance",
                                selection=sel["name"],  # "1X", "12", "X2"
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=datetime.utcnow().isoformat() + "Z",
                            ))

                    # =========================
                    # 3) Over / Under
                    # =========================
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

                    # =========================
                    # 4) Ambas Marcam
                    # =========================
                    if key == "both_teams_to_score":
                        for sel in selections:
                            out.append(Odds(
                                event_id=str(uuid.uuid4()),
                                home_team=home,
                                away_team=away,
                                league=league,
                                market="btts",
                                selection=sel["name"],  # yes / no
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=datetime.utcnow().isoformat() + "Z",
                            ))

                    # =========================
                    # 5) Handicap Asiático
                    # =========================
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
                                timestamp=datetime.utcnow().isoformat() + "Z",
                            ))

            except Exception:
                continue

        return out
