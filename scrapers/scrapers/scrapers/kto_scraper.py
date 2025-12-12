from scrapers.base import BaseScraper
from models.odds import Odds
from typing import List
from datetime import datetime
import uuid
from playwright.async_api import async_playwright
import asyncio

class KTOScraper(BaseScraper):
    name = "kto"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        url = "https://www.kto.com/br/esportes/futebol/"
        out: List[Odds] = []
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
                page = await browser.new_page()
                await page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117 Safari/537.36"})
                await page.goto(url, timeout=60000)
                await page.wait_for_timeout(2000)

                rows = await page.query_selector_all("div.event, div.match-row, .eventRow")
                for r in rows:
                    try:
                        home_el = await (r.query_selector(".team-home") or r.query_selector(".home") or r.query_selector(".homeTeam"))
                        away_el = await (r.query_selector(".team-away") or r.query_selector(".away") or r.query_selector(".awayTeam"))
                        odd_el = await (r.query_selector(".odd-home") or r.query_selector(".odds") or r.query_selector(".price"))

                        if not home_el or not away_el or not odd_el:
                            continue
                        home = (await home_el.inner_text()).strip()
                        away = (await away_el.inner_text()).strip()
                        odd_val = float((await odd_el.inner_text()).strip().replace(",", "."))

                        ev_id = str(uuid.uuid4())
                        out.append(Odds(
                            event_id=ev_id,
                            home_team=home,
                            away_team=away,
                            league="KTO",
                            sport="soccer",
                            market="1X2",
                            selection="home",
                            odds=odd_val,
                            bookmaker=self.name,
                            timestamp=datetime.utcnow().isoformat()+"Z",
                            start_time=datetime.utcnow().isoformat()+"Z"
                        ))
                    except Exception:
                        continue
                try:
                    await browser.close()
                except Exception:
                    pass
        except Exception:
            return []
        return out
