import aiohttp
import uuid
from datetime import datetime
from typing import List

from scrapers.base import BaseScraper
from models.odds import Odds

# Normalização padrão do sistema
from utils.normalize import (
    clean_team_name,
    clean_league_name,
    clean_selection_name,
)


API_URL = (
    "https://1xbet.com/LineFeed/Get1x2?"
    "sport=1&count=200&lng=en&cfview=0&isGuest=1"
)


class OneXBetScraper(BaseScraper):
    name = "1xbet"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        results: List[Odds] = []

        # =============================
        # 1) Chamada da API real
        # =============================
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API_URL, timeout=15) as resp:
                    raw = await resp.json()
        except Exception as e:
            print("[1XBET] API error:", e)
            return results

        events = raw.get("Value", [])
        timestamp = datetime.utcnow().isoformat() + "Z"

        # =============================
        # 2) Processar eventos
        # =============================
        for ev in events:
            try:
                home = clean_team_name(ev["O1"])
                away = clean_team_name(ev["O2"])
                league = clean_league_name(ev.get("L", ""))

                start_time = ev.get("S")  # timestamp UNIX da 1xbet (opcional)

                # ID determinístico (único por evento)
                event_id = str(
                    uuid.uuid5(
                        uuid.NAMESPACE_DNS,
                        f"{home}-{away}-{start_time}-1xbet"
                    )
                )

                odds = ev.get("E", [])

                if len(odds) < 3:
                    # algumas ligas não têm odds de empate, mas para surebet sempre focamos no mínimo:
                    # home / away
                    pass

                # =============================
                # MERCADO 1X2
                # =============================
                if len(odds) >= 1:
                    results.append(
                        Odds(
                            event_id=event_id,
                            home_team=home,
                            away_team=away,
                            league=league,
                            sport="soccer",
                            market="1x2",
                            selection="home",
                            odds=float(odds[0]["C"]),
                            bookmaker=self.name,
                            timestamp=timestamp,
                            start_time=start_time,
                        )
                    )

                if len(odds) >= 2:
                    results.append(
                        Odds(
                            event_id=event_id,
                            home_team=home,
                            away_team=away,
                            league=league,
                            sport="soccer",
                            market="1x2",
                            selection="away",
                            odds=float(odds[1]["C"]),
                            bookmaker=self.name,
                            timestamp=timestamp,
                            start_time=start_time,
                        )
                    )

                # Existem APIs alternativas da 1xBet que têm "draw", mas esta (Get1x2)
                # retorna geralmente apenas home/away neste endpoint simplificado.

            except Exception as e:
                print("[1XBET PARSE ERROR]", e)
                continue

        return results
