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

PINNACLE_API = "https://guest.api.arcadia.pinnacle.com/0.1/sports/29/markets/straight"


class PinnacleScraper(BaseScraper):
    name = "pinnacle"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        out: List[Odds] = []

        # ===============================
        # 1) CHAMADA DE API
        # ===============================
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(PINNACLE_API, timeout=20) as resp:
                    data = await resp.json()
        except Exception as e:
            print(f"[Pinnacle ERROR] {e}")
            return out

        events = data.get("events", [])
        periods = data.get("periods", [])
        prices = data.get("prices", [])
        participants = data.get("participants", [])

        # ===============================
        # 2) INDEXAÇÃO
        # ===============================
        team_name = {p["id"]: clean_team_name(p["name"]) for p in participants}

        price_index = {}
        for p in prices:
            # type = moneyline / spread / total
            # side = home/away/draw ou over/under
            key = (p["eventId"], p["period"], p["type"], p["side"])
            price_index[key] = p

        # ===============================
        # 3) PROCESSAR EVENTOS
        # ===============================
        for ev in events:
            event_id_raw = ev["id"]
            start_time = ev.get("startTime")
            league = clean_league_name(ev.get("league", "Pinnacle"))

            home_id = ev.get("homeId")
            away_id = ev.get("awayId")

            if home_id not in team_name or away_id not in team_name:
                continue

            home = team_name[home_id]
            away = team_name[away_id]

            # Melhor event_id: estável e igual para todos os mercados
            event_uid = str(
                uuid.uuid5(uuid.NAMESPACE_DNS, f"pinnacle-{home}-{away}-{start_time}")
            )

            timestamp = datetime.utcnow().isoformat() + "Z"

            # ===============================
            # 4) MERCADO 1X2 (moneyline)
            # ===============================
            for side in ["home", "draw", "away"]:
                key = (event_id_raw, 0, "moneyline", side)
                if key in price_index:
                    px = price_index[key]["price"]

                    out.append(
                        Odds(
                            event_id=event_uid,
                            home_team=home,
                            away_team=away,
                            league=league,
                            market="1x2",
                            selection=clean_selection_name(side),
                            odds=float(px),
                            bookmaker=self.name,
                            timestamp=timestamp,
                            start_time=start_time,
                            sport="soccer",
                        )
                    )

            # ===============================
            # 5) OVER/UNDER (total)
            # ===============================
            for p in periods:
                if p["eventId"] == event_id_raw and p["type"] == "total":
                    pts = p["points"]

                    # OVER
                    key_over = (event_id_raw, 0, "total", "over")
                    if key_over in price_index:
                        out.append(
                            Odds(
                                event_id=event_uid,
                                home_team=home,
                                away_team=away,
                                league=league,
                                market="over_under",
                                selection=f"over {pts}",
                                odds=float(price_index[key_over]["price"]),
                                bookmaker=self.name,
                                timestamp=timestamp,
                                start_time=start_time,
                                sport="soccer",
                            )
                        )

                    # UNDER
                    key_under = (event_id_raw, 0, "total", "under")
                    if key_under in price_index:
                        out.append(
                            Odds(
                                event_id=event_uid,
                                home_team=home,
                                away_team=away,
                                league=league,
                                market="over_under",
                                selection=f"under {pts}",
                                odds=float(price_index[key_under]["price"]),
                                bookmaker=self.name,
                                timestamp=timestamp,
                                start_time=start_time,
                                sport="soccer",
                            )
                        )

            # ===============================
            # 6) HANDICAP ASIÁTICO (spread)
            # ===============================
            for p in periods:
                if p["eventId"] == event_id_raw and p["type"] == "spread":
                    handicap = p["points"]

                    for side in ["home", "away"]:
                        key_spread = (event_id_raw, 0, "spread", side)
                        if key_spread in price_index:
                            out.append(
                                Odds(
                                    event_id=event_uid,
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    market="ah",
                                    selection=f"{side} {handicap}",
                                    odds=float(price_index[key_spread]["price"]),
                                    bookmaker=self.name,
                                    timestamp=timestamp,
                                    start_time=start_time,
                                    sport="soccer",
                                )
                            )

        return out
