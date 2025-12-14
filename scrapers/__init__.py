from .pinnacle import PinnacleScraper
from .stake import StakeScraper
from .xb1 import OneXBetScraper
from .xb22 import TwentyTwoBetScraper
from .bwin import BwinScraper

SCRAPERS = [
    PinnacleScraper(),
    StakeScraper(),
    OneXBetScraper(),
    TwentyTwoBetScraper(),
    BwinScraper(),
]
