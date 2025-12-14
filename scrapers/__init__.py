from .pinnacle import PinnacleScraper
from .stake import StakeScraper
from .betano import BetanoScraper
from .sportingbet import SportingbetScraper
from .kto import KTOScraper

SCRAPERS = [
    PinnacleScraper(),
    StakeScraper(),
    BetanoScraper(),
    SportingbetScraper(),
    KTOScraper(),
]
