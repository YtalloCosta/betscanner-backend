class BaseScraper:
    def __init__(self):
        pass

    async def fetch_odds(self):
        raise NotImplementedError("Implement in subclass")
