from scrapers.base import BaseScraper
from models.odds import Odds
from typing import List

class BetfairScraperTemplate(BaseScraper):
    name = "betfair_template"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        """
        TEMPLATE: Betfair tem Exchange API (recomendado).
        Prefira usar API oficial.
        """
        return []
