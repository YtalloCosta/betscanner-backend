import aiohttp
import uuid
from datetime import datetime
from typing import List

from scrapers.base import BaseScraper
from models.odds import Odds

from utils.normalize import (
    clean_team_name,
    clean_league_name,
    clean_market_name,
    clean_selection_name
)

# API OFICIAL PÚBLICA DA 1XBET (Guest)
API_URL = (
    "https://1xbet.com/LineFeed/Get1x2?"
    "sport=1&count=100&lng=en&cfview=0&isGuest=1"
)


class OneXBetScraper(BaseScraper):
    name = "1xbet"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        out: List[Odds] = []

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API_URL, timeout=20) as resp:
                    data = await resp.json()
        except Exception as e:
            print(f"[1XBET ERROR] {e}")
            return out

        events = data.get("Value", [])
        timestamp = datetime.utcnow().isoformat() + "Z"

        for ev in events:
            try:
                # ===============================
                # Times e Liga
                # ===============================
                home = clean_team_name(ev.get("O1"))
                away = clean_team_name(ev.get("O2"))
                league = clean_league_name(ev.get("L", ""))

                start_time = ev.get("S")  # timestamp UNIX

                if not home or not away:
                    continue

                # event_id único e estável
                event_uid = str(
                    uuid.uuid5(uuid.NAMESPACE_DNS, f"1xbet-{home}-{away}-{start_time}")
                )

                # ===============================
                # Odds 1X2
                # ===============================
                odds_1x2 = ev.get("E", [])
                # Estrutura real:
                # 0 → Home
                # 1 → Draw
                # 2 → Away

                if len(odds_1x2) >= 3:
                    # Home
                    out.append(
                        Odds(
                            event_id=event_uid,
                            home_team=home,
                            away_team=away,
                            league=league,
                            sport="soccer",
                            market="1x2",
                            selection="home",
                            odds=float(odds_1x2[0]["C"]),
                            bookmaker=self.name,
                            timestamp=timestamp,
                            start_time=start_time,
                        )
                    )

                    # Draw
                    out.append(
                        Odds(
                            event_id=event_uid,
                            home_team=home,
                            away_team=away,
                            league=league,
                            sport="soccer",
                            market="1x2",
                            selection="draw",
                            odds=float(odds_1x2[1]["C"]),
                            bookmaker=self.name,
                            timestamp=timestamp,
                            start_time=start_time,
                        )
                    )

                    # Away
                    out.append(
                        Odds(
                            event_id=event_uid,
                            home_team=home,
                            away_team=away,
                            league=league,
                            sport="soccer",
                            market="1x2",
                            selection="away",
                            odds=float(odds_1x2[2]["C"]),
                            bookmaker=self.name,
                            timestamp=timestamp,
                            start_time=start_time,
                        )
                    )

            except Exception as e:
                print(f"[1XBET PARSE ERROR] {e}")
                continue

        return out
