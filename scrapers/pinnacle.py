import aiohttp
import uuid
from datetime import datetime
from typing import List

from scrapers.base import BaseScraper
from models.odds import Odds

from utils.normalize import (
    clean_team_name,
    clean_market_name,
    clean_selection_name,
    clean_league_name
)

API_URL = "https://guest.api.arcadia.pinnacle.com/0.1/sports/29/markets/straight"


class PinnacleScraper(BaseScraper):
    name = "pinnacle"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        out: List[Odds] = []

        # ================================
        # 1) CHAMADA REAL À API DA PINNACLE
        # ================================
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API_URL, timeout=20) as resp:
                    data = await resp.json()
        except Exception as e:
            print("[PINNACLE] API error:", e)
            return out

        events = data.get("events", [])
        participants = data.get("participants", [])
        prices = data.get("prices", [])
        periods = data.get("periods", [])

        # index rápido dos participantes
        team_index = {p["id"]: clean_team_name(p["name"]) for p in participants}

        # index de preços
        price_index = {}
        for p in prices:
            key = (p["eventId"], p["period"], p["type"], p["side"])
            price_index[key] = p

        # ================================
        # 2) PROCESSAR CADA EVENTO
        # ================================
        for ev in events:
            try:
                event_id_raw = ev["id"]

                home_id = ev.get("homeId")
                away_id = ev.get("awayId")
                league = clean_league_name(ev.get("league", "Pinnacle"))

                if home_id not in team_index or away_id not in team_index:
                    continue

                home = team_index[home_id]
                away = team_index[away_id]

                timestamp = datetime.utcnow().isoformat() + "Z"

                # Um único event_id universal para o evento
                event_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{home}-{away}-{league}"))

                # ================================
                # 3) MERCADO 1X2 (MONEYLINE)
                # ================================
                sides_map = {
                    "home": "home",
                    "draw": "draw",
                    "away": "away",
                }

                for side in sides_map:
                    key = (event_id_raw, 0, "moneyline", side)
                    if key in price_index:
                        odds = float(price_index[key]["price"])

                        out.append(
                            Odds(
                                event_id=event_id,
                                home_team=home,
                                away_team=away,
                                league=league,
                                sport="soccer",
                                market="1x2",
                                selection=side,
                                odds=odds,
                                bookmaker=self.name,
                                timestamp=timestamp
                            )
                        )

                # ================================
                # 4) DUPLA CHANCE (COMBINADA)
                # ================================
                def safe_get(key):
                    return float(price_index[key]["price"]) if key in price_index else None

                key_home = (event_id_raw, 0, "moneyline", "home")
                key_draw = (event_id_raw, 0, "moneyline", "draw")
                key_away = (event_id_raw, 0, "moneyline", "away")

                # 1X
                if key_home in price_index and key_draw in price_index:
                    dc = 1 / (1 / safe_get(key_home) + 1 / safe_get(key_draw))
                    out.append(
                        Odds(
                            event_id=event_id,
                            home_team=home,
                            away_team=away,
                            league=league,
                            sport="soccer",
                            market="double_chance",
                            selection="1X",
                            odds=dc,
                            bookmaker=self.name,
                            timestamp=timestamp
                        )
                    )

                # X2
                if key_away in price_index and key_draw in price_index:
                    dc = 1 / (1 / safe_get(key_away) + 1 / safe_get(key_draw))
                    out.append(
                        Odds(
                            event_id=event_id,
                            home_team=home,
                            away_team=away,
                            league=league,
                            sport="soccer",
                            market="double_chance",
                            selection="X2",
                            odds=dc,
                            bookmaker=self.name,
                            timestamp=timestamp
                        )
                    )

                # 12
                if key_home in price_index and key_away in price_index:
                    dc = 1 / (1 / safe_get(key_home) + 1 / safe_get(key_away))
                    out.append(
                        Odds(
                            event_id=event_id,
                            home_team=home,
                            away_team=away,
                            league=league,
                            sport="soccer",
                            market="double_chance",
                            selection="12",
                            odds=dc,
                            bookmaker=self.name,
                            timestamp=timestamp
                        )
                    )

                # ================================
                # 5) OVER/UNDER PRINCIPAL
                # ================================
                for p in periods:
                    if p["eventId"] != event_id_raw:
                        continue
                    if p["type"] != "total":
                        continue

                    points = p["points"]

                    key_over = (event_id_raw, 0, "total", f"over_{points}")
                    key_under = (event_id_raw, 0, "total", f"under_{points}")

                    if key_over in price_index:
                        out.append(
                            Odds(
                                event_id=event_id,
                                home_team=home,
                                away_team=away,
                                league=league,
                                sport="soccer",
                                market="over_under",
                                selection=f"over {points}",
                                odds=float(price_index[key_over]["price"]),
                                bookmaker=self.name,
                                timestamp=timestamp
                            )
                        )

                    if key_under in price_index:
                        out.append(
                            Odds(
                                event_id=event_id,
                                home_team=home,
                                away_team=away,
                                league=league,
                                sport="soccer",
                                market="over_under",
                                selection=f"under {points}",
                                odds=float(price_index[key_under]["price"]),
                                bookmaker=self.name,
                                timestamp=timestamp
                            )
                        )

                # ================================
                # 6) HANDICAP ASIÁTICO PRINCIPAL
                # ================================
                for p in periods:
                    if p["eventId"] != event_id_raw:
                        continue
                    if p["type"] != "spread":
                        continue

                    handicap = p["points"]

                    for side in ["home", "away"]:
                        key_sp = (event_id_raw, 0, "spread", f"{side}_{handicap}")

                        if key_sp in price_index:
                            out.append(
                                Odds(
                                    event_id=event_id,
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    sport="soccer",
                                    market="asian_handicap",
                                    selection=f"{side} {handicap}",
                                    odds=float(price_index[key_sp]["price"]),
                                    bookmaker=self.name,
                                    timestamp=timestamp
                                )
                            )

            except Exception as e:
                print("[PINNACLE PARSE ERROR]", e)
                continue

        return out
