from scrapers.base import BaseScraper
from models.odds import Odds
from typing import List

class OneXBetScraperTemplate(BaseScraper):
    name = "1xbet_template"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        """
        TEMPLATE para 1xBet. 1xBet pode bloquear scraping agressivo.
        Use com cautela e contabilize proxies e rotatividade.
        """
        return []
