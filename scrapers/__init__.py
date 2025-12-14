from .pinnacle import PinnacleScraper
from .stake import StakeScraper
from .betano import BetanoScraper
from .sportingbet import SportingBetScraper
from .kto import KTOScraper
from .bwin import BwinScraper
from .xb1 import OneXBetScraper
from .xb22 import TwentyTwoBetScraper


SCRAPERS = [
    PinnacleScraper(),
    StakeScraper(),
    BetanoScraper(),
    SportingBetScraper(),
    KTOScraper(),
    BwinScraper(),
    OneXBetScraper(),
    TwentyTwoBetScraper(),
]
