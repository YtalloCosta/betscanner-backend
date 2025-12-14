import uuid
import asyncio
from datetime import datetime
from typing import List
from scrapers.base import BaseScraper
from models.odds import Odds
from playwright.async_api import async_playwright

class BetanoScraper(BaseScraper):
    name = "betano"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        url = "https://br.betano.com/sport/futebol/"

        out: List[Odds] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            page = await browser.new_page()

            await page.goto(url, timeout=60000)
            await page.wait_for_timeout(5000)

            events = await page.query_selector_all(".event-row")

            for ev in events:
                try:
                    home = await ev.query_selector_eval(".team .home", "el => el.innerText")
                    away = await ev.query_selector_eval(".team .away", "el => el.innerText")

                    odds_el = await ev.query_selector_all(".selections .odd")
                    if len(odds_el) < 2:
                        continue

                    odd_home = float((await odds_el[0].inner_text()).replace(",", "."))
                    odd_away = float((await odds_el[1].inner_text()).replace(",", "."))

                    out.append(Odds(
                        event_id=str(uuid.uuid4()),
                        home_team=home,
                        away_team=away,
                        league="Futebol",
                        market="1x2",
                        selection="home",
                        odds=odd_home,
                        bookmaker=self.name,
                        timestamp=datetime.utcnow().isoformat() + "Z"
                    ))

                    out.append(Odds(
                        event_id=str(uuid.uuid4()),
                        home_team=home,
                        away_team=away,
                        league="Futebol",
                        market="1x2",
                        selection="away",
                        odds=odd_away,
                        bookmaker=self.name,
                        timestamp=datetime.utcnow().isoformat() + "Z"
                    ))
                except:
                    continue

            await browser.close()

        return out
