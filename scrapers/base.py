from typing import List
from ..models.odds import Odds

class BaseScraper:
    name = "base"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        """Return list[Odds] for next days_ahead days."""
        raise NotImplementedError
