import aiohttp
import uuid
from datetime import datetime
from typing import List

from scrapers.base import BaseScraper
from models.odds import Odds

from utils.normalize import (
    clean_team_name,
    clean_league_name,
    clean_selection_name
)

API_URL = (
    "https://22bet.com/LineFeed/Get1x2?"
    "sport=1&count=100&lng=en&isGuest=1"
)


class TwentyTwoBetScraper(BaseScraper):
    name = "22bet"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        out: List[Odds] = []

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API_URL, timeout=20) as resp:
                    data = await resp.json()
        except Exception as e:
            print(f"[22BET API ERROR] {e}")
            return out

        events = data.get("Value", [])
        timestamp = datetime.utcnow().isoformat() + "Z"

        for ev in events:
            try:
                # ============================
                # TIMES E LIGA
                # ============================
                home = clean_team_name(ev.get("O1"))
                away = clean_team_name(ev.get("O2"))
                league = clean_league_name(ev.get("L", ""))

                start_time = ev.get("S")  # epoch timestamp

                if not home or not away:
                    continue

                # event_id único e estável
                event_uid = str(
                    uuid.uuid5(uuid.NAMESPACE_DNS, f"22bet-{home}-{away}-{start_time}")
                )

                # ============================
                # 1X2 COMPLETO (Home / Draw / Away)
                # ============================
                odds = ev.get("E", [])

                if len(odds) >= 3:
                    # HOME
                    out.append(
                        Odds(
                            event_id=event_uid,
                            home_team=home,
                            away_team=away,
                            league=league,
                            sport="soccer",
                            market="1x2",
                            selection="home",
                            odds=float(odds[0]["C"]),
                            bookmaker=self.name,
                            timestamp=timestamp,
                            start_time=start_time
                        )
                    )

                    # DRAW
                    out.append(
                        Odds(
                            event_id=event_uid,
                            home_team=home,
                            away_team=away,
                            league=league,
                            sport="soccer",
                            market="1x2",
                            selection="draw",
                            odds=float(odds[1]["C"]),
                            bookmaker=self.name,
                            timestamp=timestamp,
                            start_time=start_time
                        )
                    )

                    # AWAY
                    out.append(
                        Odds(
                            event_id=event_uid,
                            home_team=home,
                            away_team=away,
                            league=league,
                            sport="soccer",
                            market="1x2",
                            selection="away",
                            odds=float(odds[2]["C"]),
                            bookmaker=self.name,
                            timestamp=timestamp,
                            start_time=start_time
                        )
                    )

            except Exception as e:
                print(f"[22BET PARSE ERROR] {e}")
                continue

        return out
