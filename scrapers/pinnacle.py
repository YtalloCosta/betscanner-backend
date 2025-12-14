import aiohttp
import uuid
from datetime import datetime
from typing import List

from scrapers.base import BaseScraper
from models.odds import Odds

PINNACLE_API = (
    "https://guest.api.arcadia.pinnacle.com/0.1/sports/29/markets/straight"
)


class PinnacleScraper(BaseScraper):
    name = "pinnacle"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        out: List[Odds] = []

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(PINNACLE_API, timeout=15) as resp:
                    data = await resp.json()
        except Exception as e:
            print(f"[PinnacleScraper] erro: {e}")
            return out

        events = data.get("events", [])
        periods = data.get("periods", [])
        prices = data.get("prices", [])
        participants = data.get("participants", [])

        # indexação rápida
        team_name = {p["id"]: p["name"] for p in participants}
        price_index = {}

        for p in prices:
            key = (p["eventId"], p["period"], p["type"], p["side"])
            price_index[key] = p

        for ev in events:
            event_id = ev["id"]

            # nomes dos times
            home_id = ev.get("homeId")
            away_id = ev.get("awayId")
            league = ev.get("league", "Pinnacle")

            if home_id not in team_name or away_id not in team_name:
                continue

            home = team_name[home_id]
            away = team_name[away_id]

            # ================================
            # 1) MERCADO 1X2 (Moneyline)
            # ================================
            for side in ["home", "draw", "away"]:
                key = (event_id, 0, "moneyline", side)
                if key in price_index:
                    odds = price_index[key].get("price")
                    if odds:
                        out.append(
                            Odds(
                                event_id=str(uuid.uuid4()),
                                home_team=home,
                                away_team=away,
                                league=league,
                                market="1x2",
                                selection=side,
                                odds=float(odds),
                                bookmaker=self.name,
                                timestamp=datetime.utcnow().isoformat() + "Z",
                            )
                        )

            # ================================
            # 2) MERCADO DUPLA CHANCE (COMPOSTO)
            # ================================
            # DC 1X
            key_1x = (event_id, 0, "moneyline", "home")
            key_x = (event_id, 0, "moneyline", "draw")
            if key_1x in price_index and key_x in price_index:
                out.append(
                    Odds(
                        event_id=str(uuid.uuid4()),
                        home_team=home,
                        away_team=away,
                        league=league,
                        market="double_chance",
                        selection="1X",
                        odds=1 / (1/price_index[key_1x]["price"] + 1/price_index[key_x]["price"]),
                        bookmaker=self.name,
                        timestamp=datetime.utcnow().isoformat() + "Z",
                    )
                )

            # DC X2
            key_away = (event_id, 0, "moneyline", "away")
            if key_x in price_index and key_away in price_index:
                out.append(
                    Odds(
                        event_id=str(uuid.uuid4()),
                        home_team=home,
                        away_team=away,
                        league=league,
                        market="double_chance",
                        selection="X2",
                        odds=1 / (1/price_index[key_x]["price"] + 1/price_index[key_away]["price"]),
                        bookmaker=self.name,
                        timestamp=datetime.utcnow().isoformat() + "Z",
                    )
                )

            # DC 12
            if key_1x in price_index and key_away in price_index:
                out.append(
                    Odds(
                        event_id=str(uuid.uuid4()),
                        home_team=home,
                        away_team=away,
                        league=league,
                        market="double_chance",
                        selection="12",
                        odds=1 / (1/price_index[key_1x]["price"] + 1/price_index[key_away]["price"]),
                        bookmaker=self.name,
                        timestamp=datetime.utcnow().isoformat() + "Z",
                    )
                )

            # ================================
            # 3) OVER/UNDER (Totals)
            # ================================
            for p in periods:
                if p["eventId"] != event_id:
                    continue
                if p["type"] == "total":
                    total_points = p["points"]

                    # over
                    key_over = (event_id, 0, "total", f"over_{total_points}")
                    if key_over in price_index:
                        out.append(
                            Odds(
                                event_id=str(uuid.uuid4()),
                                home_team=home,
                                away_team=away,
                                league=league,
                                market="over_under",
                                selection=f"over {total_points}",
                                odds=float(price_index[key_over]["price"]),
                                bookmaker=self.name,
                                timestamp=datetime.utcnow().isoformat() + "Z",
                            )
                        )

                    # under
                    key_under = (event_id, 0, "total", f"under_{total_points}")
                    if key_under in price_index:
                        out.append(
                            Odds(
                                event_id=str(uuid.uuid4()),
                                home_team=home,
                                away_team=away,
                                league=league,
                                market="over_under",
                                selection=f"under {total_points}",
                                odds=float(price_index[key_under]["price"]),
                                bookmaker=self.name,
                                timestamp=datetime.utcnow().isoformat() + "Z",
                            )
                        )

            # ================================
            # 4) HANDICAP ASIÁTICO (Spread)
            # ================================
            for p in periods:
                if p["eventId"] != event_id:
                    continue
                if p["type"] == "spread":
                    handicap = p["points"]

                    for side in ["home", "away"]:
                        key_sp = (event_id, 0, "spread", f"{side}_{handicap}")
                        if key_sp in price_index:
                            out.append(
                                Odds(
                                    event_id=str(uuid.uuid4()),
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    market="asian_handicap",
                                    selection=f"{side} {handicap}",
                                    odds=float(price_index[key_sp]["price"]),
                                    bookmaker=self.name,
                                    timestamp=datetime.utcnow().isoformat() + "Z",
                                )
                            )

        return out

