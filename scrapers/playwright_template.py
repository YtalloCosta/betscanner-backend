from scrapers.base import BaseScraper
from models.odds import Odds
from typing import List
from datetime import datetime, timedelta
import uuid
from playwright.async_api import async_playwright, TimeoutError as PWTimeout
import asyncio

class PlaywrightTemplateScraper(BaseScraper):
    name = "example_playwright"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        out: List[Odds] = []
        now = datetime.utcnow()

        # Loop por cada dia (0 = hoje, 1 = amanhã, ...)
        for d in range(days_ahead):
            target_day = now + timedelta(days=d)
            # Se o site aceitar querystring com data, construa a URL aqui.
            # Ex: url = f"https://example-bookmaker.com/fixtures?date={target_day.date().isoformat()}"
            url = "https://example-bookmaker.com/fixtures"  # TODO: alterar para site real

            # Tente abrir Playwright / Chromium
            browser = None
            try:
                async with async_playwright() as pw:
                    # flags importantes para rodar em containers
                    browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
                    page = await browser.new_page()
                    # Acesse a página (aumente timeout se o site for lento)
                    await page.goto(url, timeout=60000)

                    # TODO: altere o seletor abaixo para o seletor real das linhas de evento no site
                    # Ex: rows = await page.query_selector_all(".fixture-row")
                    await page.wait_for_timeout(500)  # pequena espera inicial
                    rows = await page.query_selector_all(".match-row")  # TODO: ajustar

                    for r in rows:
                        try:
                            # ---- EXEMPLO DE EXTRAÇÃO: ajuste os seletores/atributos ----
                            # home = (await r.query_selector_eval(".home", "e => e.innerText")).strip()
                            # away = (await r.query_selector_eval(".away", "e => e.innerText")).strip()
                            # odd_home = float((await r.query_selector_eval(".odd-home", "e => e.innerText")).strip())
                            # start_time_str = await r.query_selector_eval(".start", "e => e.getAttribute('data-start') || e.innerText")
                            #
                            # Substitua os seletores acima pelos corretos do site real.
                            #
                            home = (await r.query_selector_eval(".home", "e => e.innerText")).strip()
                            away = (await r.query_selector_eval(".away", "e => e.innerText")).strip()

                            # Exemplo: tentar pegar odd; se não existir, pula
                            try:
                                odd_home_raw = await r.query_selector_eval(".odd-home", "e => e.innerText")
                                odd_home = float(odd_home_raw.replace(",", "."))
                            except Exception:
                                continue

                            # Tentar extrair start_time (preferir ISO se disponível)
                            try:
                                start_time_raw = await r.query_selector_eval(".start", "e => e.getAttribute('data-start') || e.innerText")
                                # normalize: se já for ISO, ok; senão, tente parse (dependente do site)
                                start_time = start_time_raw.strip()
                            except Exception:
                                start_time = (target_day.isoformat() + "T00:00:00Z")

                            ev_id = str(uuid.uuid4())

                            out.append(Odds(
                                event_id=ev_id,
                                home_team=home,
                                away_team=away,
                                league="Example League",  # TODO: ajustar se possível
                                sport="soccer",            # TODO: ajustar conforme a fonte
                                market="1X2",
                                selection="home",
                                odds=odd_home,
                                bookmaker=self.name,
                                timestamp=datetime.utcnow().isoformat() + "Z",
                                start_time=start_time
                            ))
                        except Exception:
                            # se falhar parse desta linha, continua para a próxima
                            continue

            except PWTimeout:
                # timeout do Playwright
                continue
            except Exception:
                # erro genérico — continue para próximo dia
                continue
            finally:
                # garantia de fechar browser caso tenha sido aberto
                try:
                    if browser:
                        await browser.close()
                except Exception:
                    pass

        return out
