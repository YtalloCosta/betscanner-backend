from .betano import BetanoScraper
from .bwin import BwinScraper
from .kto import KTOScraper
from .pinnacle import PinnacleScraper
from .stake import StakeScraper
from .xb1 import OneXBetScraper
from .xb22 import TwentyTwoBetScraper
from .sportingbet import SportingbetScraper


SCRAPERS = [
    BetanoScraper(),
    BwinScraper(),
    KTOScraper(),
    PinnacleScraper(),
    StakeScraper(),
    OneXBetScraper(),
    TwentyTwoBetScraper(),
    SportingbetScraper(),
]
