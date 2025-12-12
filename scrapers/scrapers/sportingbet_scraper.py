from scrapers.base import BaseScraper
from models.odds import Odds
from typing import List
from datetime import datetime
import uuid
from playwright.async_api import async_playwright
import asyncio

class SportingBetScraper(BaseScraper):
    name = "sportingbet"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        url = "https://sports.sportingbet.com/pt-br/sports/futebol-4"
        out: List[Odds] = []
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
                page = await browser.new_page()
                await page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117 Safari/537.36"})
                await page.goto(url, timeout=70000)
                # esperar que eventos carreguem (ajuste o seletor se precisar)
                try:
                    await page.wait_for_selector("ms-event, .eventRow, .match-row", timeout=15000)
                except Exception:
                    pass

                rows = await page.query_selector_all("ms-event, .eventRow, .match-row")
                for r in rows:
                    try:
                        # múltiplas abordagens para extrair nomes e odds
                        home_el = await (r.query_selector(".home") or r.query_selector(".event-name--home") or r.query_selector(".team--home"))
                        away_el = await (r.query_selector(".away") or r.query_selector(".event-name--away") or r.query_selector(".team--away"))
                        odd_el = await (r.query_selector(".kambiBC-bet-offer__outcome__odds") or r.query_selector(".odds") or r.query_selector(".price"))

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
                            league="Sportingbet",
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
