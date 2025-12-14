import uuid
from datetime import datetime
from typing import List
from playwright.async_api import async_playwright
from scrapers.base import BaseScraper
from models.odds import Odds


class SportingbetScraper(BaseScraper):
    name = "sportingbet"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        url = "https://sports.sportingbet.com/pt-br/sports/futebol-4"

        out: List[Odds] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )

            page = await browser.new_page()
            await page.goto(url, timeout=60000)
            await page.wait_for_timeout(5000)

            rows = await page.query_selector_all("ms-event, .eventRow, .match-row")

            for r in rows:
                try:
                    home = await r.query_selector_eval(".ms-event-name .home, .team--home", "e => e.innerText").strip()
                    away = await r.query_selector_eval(".ms-event-name .away, .team--away", "e => e.innerText").strip()

                    odd_home = float(
                        (await r.query_selector_eval(".odd--home, .price", "e => e.innerText"))
                        .replace(",", ".")
                    )
                    odd_away = float(
                        (await r.query_selector_eval(".odd--away, .price", "e => e.innerText"))
                        .replace(",", ".")
                    )

                    out.append(Odds(
                        event_id=str(uuid.uuid4()),
                        home_team=home,
                        away_team=away,
                        league="Sportingbet",
                        market="1x2",
                        selection="home",
                        odds=odd_home,
                        bookmaker=self.name,
                        timestamp=datetime.utcnow().isoformat() + "Z",
                    ))

                    out.append(Odds(
                        event_id=str(uuid.uuid4()),
                        home_team=home,
                        away_team=away,
                        league="Sportingbet",
                        market="1x2",
                        selection="away",
                        odds=odd_away,
                        bookmaker=self.name,
                        timestamp=datetime.utcnow().isoformat() + "Z",
                    ))

                except Exception:
                    continue

            await browser.close()

        return out
