from .base import BaseScraper
from .bet365 import Bet365Scraper
from .bet365_template import Bet365Template
from .betfair_template import BetfairTemplate
from .betano import BetanoScraper
from .betano_scraper import BetanoTemplate
from .kto_scraper import KtoScraper
from .mock_scraper import MockScraper
from .pinnacle import PinnacleScraper
from .playwright_template import PlaywrightTemplate
from .sportingbet import SportingBetScraper
from .sportingbet_scraper import SportingbetTemplate
from .x1bet_template import OneXBetScraperTemplate

SCRAPERS = [
    Bet365Scraper(),
    BetanoScraper(),
    PinnacleScraper(),
    SportingBetScraper(),
    KtoScraper(),
    # adicione outros aqui conforme forem ficando prontos
]
