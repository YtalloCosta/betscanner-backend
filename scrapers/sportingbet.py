import asyncio
import json
from datetime import datetime
from typing import List
from playwright.async_api import async_playwright

from scrapers.base import BaseScraper
from models.odds import Odds


class SportingbetScraper(BaseScraper):
    name = "sportingbet"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        out: List[Odds] = []

        PAGE_URL = "https://sports.sportingbet.com/pt-br/sports/futebol-4"
        API_URL = "https://sports.sportingbet.com/api/sportsbook/events"

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            page = await browser.new_page()

            await page.goto(PAGE_URL, timeout=60000)
            await page.wait_for_timeout(4000)

            # pega token guardado no localStorage
            token = await page.evaluate("""
                () => window.localStorage.getItem('auth.access_token')
            """)

            if not token:
                return out

            headers = {"authorization": f"Bearer {token}"}

            params = {
                "sports": "4",
                "limit": 50,
                "offset": 0
            }

            response = await page.request.get(API_URL, headers=headers, params=params)

            if response.ok:
                data = await response.json()

                for event in data.get("events", []):
                    try:
                        out.append(
                            Odds(
                                bookmaker=self.name,
                                event_id=str(event.get("id")),
                                home=event["name"]["value"].split(" vs ")[0],
                                away=event["name"]["value"].split(" vs ")[1],
                                date=datetime.fromtimestamp(event["startTime"] / 1000),
                                markets=[],
                            )
                        )
                    except:
                        continue

            await browser.close()

        return out
