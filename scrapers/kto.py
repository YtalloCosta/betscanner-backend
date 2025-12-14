import uuid
from datetime import datetime
from typing import List
from playwright.async_api import async_playwright
from scrapers.base import BaseScraper
from models.odds import Odds


class KTOScraper(BaseScraper):
    name = "kto"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        url = "https://kto.com/sports/futebol/"

        out: List[Odds] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            page = await browser.new_page()
            await page.goto(url, timeout=60000)
            await page.wait_for_timeout(5000)

            rows = await page.query_selector_all(".event-row")

            for r in rows:
                try:
                    home = await r.query_selector_eval(".team.home", "e => e.innerText")
                    away = await r.query_selector_eval(".team.away", "e => e.innerText")

                    odds_el = await r.query_selector_all(".odds .selection")
                    if len(odds_el) < 2:
                        continue

                    odd_home = float((await odds_el[0].inner_text()).replace(",", "."))
                    odd_away = float((await odds_el[1].inner_text()).replace(",", "."))

                    out.append(Odds(
                        event_id=str(uuid.uuid4()),
                        home_team=home,
                        away_team=away,
                        league="KTO",
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
                        league="KTO",
                        market="1x2",
                        selection="away",
                        odds=odd_away,
                        bookmaker=self.name,
                        timestamp=datetime.utcnow().isoformat() + "Z"
                    ))

                except Exception:
                    continue

            await browser.close()

        return out
