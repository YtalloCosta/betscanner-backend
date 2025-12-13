from .pinnacle import PinnacleScraper
from .stake import StakeScraper
from .xbet_1 import OneXBetScraper
from .xbet_22 import TwentyTwoBetScraper
from .bwin import BwinScraper

# Lista oficial de scrapers ativos
SCRAPERS = [
    PinnacleScraper(),
    StakeScraper(),
    OneXBetScraper(),
    TwentyTwoBetScraper(),
    BwinScraper(),
]
