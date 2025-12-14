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
    clean_selection_name,
)

API_URL = (
    "https://gaming-int.bwin.com/cms/api/event?"
    "lang=pt-br&sportIds=4&isHighlighted=false&skip=0&take=200"
)


class BwinScraper(BaseScraper):
    name = "bwin"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        results: List[Odds] = []

        # ================================
        # 1) CHAMADA À API REAL
        # ================================
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API_URL, timeout=20) as resp:
                    data = await resp.json()
        except Exception as e:
            print("[BWIN] API erro:", e)
            return results

        events = data.get("events", [])

        # ================================
        # 2) PROCESSAR EVENTOS
        # ================================
        for ev in events:
            try:
                league = clean_league_name(ev.get("competition", {}).get("name", "Bwin"))

                home = clean_team_name(ev["participants"][0]["name"])
                away = clean_team_name(ev["participants"][1]["name"])

                start_time = ev.get("startDate")
                timestamp = datetime.utcnow().isoformat() + "Z"

                # event_id universal
                event_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{home}-{away}-{start_time}"))

                markets = ev.get("markets", [])

                # flags para evitar linhas secundárias
                found_ou = False
                found_ah = False

                for m in markets:
                    key = m.get("key", "").lower()
                    selections = m.get("outcomes", [])

                    # ================================
                    # 1) MERCADO 1X2
                    # ================================
                    if key in ["3way", "match_result", "1x2"]:
                        for sel in selections:
                            selection = clean_selection_name(sel["name"])
                            odds = float(sel["odds"])

                            results.append(
                                Odds(
                                    event_id=event_id,
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    sport="soccer",
                                    market="1x2",
                                    selection=selection,
                                    odds=odds,
                                    bookmaker=self.name,
                                    timestamp=timestamp,
                                    start_time=start_time,
                                )
                            )

                    # ================================
                    # 2) DUPLA CHANCE
                    # ================================
                    if key in ["double_chance", "dc"]:
                        for sel in selections:
                            selection = sel["name"].upper()
                            odds = float(sel["odds"])

                            results.append(
                                Odds(
                                    event_id=event_id,
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    sport="soccer",
                                    market="double_chance",
                                    selection=selection,
                                    odds=odds,
                                    bookmaker=self.name,
                                    timestamp=timestamp,
                                    start_time=start_time,
                                )
                            )

                    # ================================
                    # 3) OVER/UNDER PRINCIPAL
                    # ================================
                    if key == "totals" and not found_ou:
                        sel = selections[0]  # a Bwin sempre lista a linha principal primeiro
                        results.append(
                            Odds(
                                event_id=event_id,
                                home_team=home,
                                away_team=away,
                                league=league,
                                sport="soccer",
                                market="over_under",
                                selection=clean_selection_name(sel["name"]),
                                odds=float(sel["odds"]),
                                bookmaker=self.name,
                                timestamp=timestamp,
                                start_time=start_time,
                            )
                        )
                        found_ou = True

                    # ================================
                    # 4) BTTS
                    # ================================
                    if key in ["both_teams_to_score", "btts"]:
                        for sel in selections:
                            selection = clean_selection_name(sel["name"])
                            odds = float(sel["odds"])

                            results.append(
                                Odds(
                                    event_id=event_id,
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    sport="soccer",
                                    market="btts",
                                    selection=selection,
                                    odds=odds,
                                    bookmaker=self.name,
                                    timestamp=timestamp,
                                    start_time=start_time,
                                )
                            )

                    # ================================
                    # 5) ASIAN HANDICAP PRINCIPAL
                    # ================================
                    if key in ["handicap", "asian_handicap"] and not found_ah:
                        sel = selections[0]  # usa só o handicap principal
                        selection = clean_selection_name(sel["name"])

                        results.append(
                            Odds(
                                event_id=event_id,
                                home_team=home,
                                away_team=away,
                                league=league,
                                sport="soccer",
                                market="asian_handicap",
                                selection=selection,
                                odds=float(sel["odds"]),
                                bookmaker=self.name,
                                timestamp=timestamp,
                                start_time=start_time,
                            )
                        )
                        found_ah = True

            except Exception as e:
                print("[BWIN] parse error:", e)
                continue

        return results
