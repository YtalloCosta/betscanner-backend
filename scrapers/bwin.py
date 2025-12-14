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

API = (
    "https://gaming-int.bwin.com/cms/api/event?"
    "lang=pt-br&sportIds=4&isHighlighted=false&skip=0&take=200"
)


class BwinScraper(BaseScraper):
    name = "bwin"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        out: List[Odds] = []

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API, timeout=20) as resp:
                    data = await resp.json()
        except Exception as e:
            print(f"[BWIN API ERROR] {e}")
            return out

        events = data.get("events", [])

        for ev in events:
            try:
                league = clean_league_name(ev["competition"]["name"])
                start_time = ev.get("startDate")
                timestamp = datetime.utcnow().isoformat() + "Z"

                home = clean_team_name(ev["participants"][0]["name"])
                away = clean_team_name(ev["participants"][1]["name"])

                event_uid = str(uuid.uuid4())  # MESMO ID para todos os mercados

                markets = ev.get("markets", [])
                if not markets:
                    continue

                # PROCESSAR CADA MERCADO
                for m in markets:
                    market_key = m.get("marketType")

                    outcomes = m.get("outcomes", [])
                    if not outcomes:
                        continue

                    # --------------------------------------------------
                    # 1) MERCADO 1x2 (WIN_DRAW_WIN)
                    # --------------------------------------------------
                    if market_key == "WINNER":
                        # bwin envia: home / draw / away em ordens locais
                        for outcome in outcomes:
                            sel_raw = outcome.get("type")
                            odds_val = float(outcome.get("odds", 0))

                            selection = clean_selection_name(sel_raw)

                            out.append(
                                Odds(
                                    event_id=event_uid,
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    market="1x2",
                                    selection=selection,
                                    odds=odds_val,
                                    bookmaker=self.name,
                                    timestamp=timestamp,
                                    start_time=start_time,
                                )
                            )

                    # --------------------------------------------------
                    # 2) BTTS
                    # --------------------------------------------------
                    if market_key == "BOTH_TEAMS_TO_SCORE":
                        for outcome in outcomes:
                            sel = clean_selection_name(outcome["type"])
                            out.append(
                                Odds(
                                    event_id=event_uid,
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    market="btts",
                                    selection=sel,  # yes/no
                                    odds=float(outcome["odds"]),
                                    bookmaker=self.name,
                                    timestamp=timestamp,
                                    start_time=start_time,
                                )
                            )

                    # --------------------------------------------------
                    # 3) OVER / UNDER
                    # --------------------------------------------------
                    if market_key == "TOTAL_POINTS":
                        for outcome in outcomes:
                            sel = outcome["type"].lower()  # "over 2.5"
                            out.append(
                                Odds(
                                    event_id=event_uid,
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    market="over_under",
                                    selection=sel,
                                    odds=float(outcome["odds"]),
                                    bookmaker=self.name,
                                    timestamp=timestamp,
                                    start_time=start_time,
                                )
                            )

                    # --------------------------------------------------
                    # 4) Handicap Asiático (quando disponível)
                    # --------------------------------------------------
                    if market_key == "HANDICAP":
                        for outcome in outcomes:
                            sel = outcome["type"]  # "home -1.0", "away +1.0"
                            out.append(
                                Odds(
                                    event_id=event_uid,
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    market="ah",
                                    selection=sel.lower(),
                                    odds=float(outcome["odds"]),
                                    bookmaker=self.name,
                                    timestamp=timestamp,
                                    start_time=start_time,
                                )
                            )

            except Exception as e:
                print(f"[BWIN PARSE ERROR] {e}")
                continue

        return out
