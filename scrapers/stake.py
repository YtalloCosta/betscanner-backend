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


class StakeScraper(BaseScraper):
    name = "stake"

    API_URL = (
        "https://api.stake.com/sports/events?"
        "sport=soccer&limit=200&marketType="
        "match_odds,double_chance,both_teams_to_score,"
        "totals,asian_handicap"
    )

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        results: List[Odds] = []

        # ========================
        # 1) CHAMADA REAL À API
        # ========================
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.API_URL, timeout=20) as resp:
                    data = await resp.json()
        except Exception as e:
            print("[STAKE] API error:", e)
            return results

        events = data.get("events", [])

        # ========================
        # 2) PROCESSAR EVENTOS
        # ========================
        for ev in events:
            try:
                # Times, liga
                home = clean_team_name(ev["homeTeam"]["name"])
                away = clean_team_name(ev["awayTeam"]["name"])
                league = clean_league_name(ev["competition"]["name"])

                start_time = ev.get("startTime")
                timestamp = datetime.utcnow().isoformat() + "Z"

                # event_id determinístico
                event_id = str(uuid.uuid5(
                    uuid.NAMESPACE_DNS,
                    f"{home}-{away}-{start_time}-{self.name}"
                ))

                markets = ev.get("markets", [])

                # ========================
                # 1x2
                # ========================
                m_1x2 = next((m for m in markets if m["key"] == "match_odds"), None)
                if m_1x2:
                    for sel in m_1x2.get("outcomes", []):
                        results.append(
                            Odds(
                                event_id=event_id,
                                home_team=home,
                                away_team=away,
                                league=league,
                                sport="soccer",
                                market="1x2",
                                selection=clean_selection_name(sel["name"]),
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=timestamp,
                                start_time=start_time,
                            )
                        )

                # ========================
                # Dupla Chance
                # ========================
                m_dc = next((m for m in markets if m["key"] == "double_chance"), None)
                if m_dc:
                    for sel in m_dc.get("outcomes", []):
                        results.append(
                            Odds(
                                event_id=event_id,
                                home_team=home,
                                away_team=away,
                                league=league,
                                sport="soccer",
                                market="double_chance",
                                selection=sel["name"],  # 1X / X2 / 12
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=timestamp,
                                start_time=start_time,
                            )
                        )

                # ========================
                # Over / Under
                # ========================
                m_ou = next((m for m in markets if m["key"] == "totals"), None)
                if m_ou:
                    for sel in m_ou.get("outcomes", []):
                        results.append(
                            Odds(
                                event_id=event_id,
                                home_team=home,
                                away_team=away,
                                league=league,
                                sport="soccer",
                                market="over_under",
                                selection=clean_selection_name(sel["name"]),
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=timestamp,
                                start_time=start_time,
                            )
                        )

                # ========================
                # Ambas Marcam (BTTS)
                # ========================
                m_btts = next((m for m in markets if m["key"] == "both_teams_to_score"), None)
                if m_btts:
                    for sel in m_btts.get("outcomes", []):
                        results.append(
                            Odds(
                                event_id=event_id,
                                home_team=home,
                                away_team=away,
                                league=league,
                                sport="soccer",
                                market="btts",
                                selection=clean_selection_name(sel["name"]),  # yes/no
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=timestamp,
                                start_time=start_time,
                            )
                        )

                # ========================
                # Handicap Asiático
                # ========================
                m_ah = next((m for m in markets if m["key"] == "asian_handicap"), None)
                if m_ah:
                    for sel in m_ah.get("outcomes", []):
                        results.append(
                            Odds(
                                event_id=event_id,
                                home_team=home,
                                away_team=away,
                                league=league,
                                sport="soccer",
                                market="asian_handicap",
                                selection=clean_selection_name(sel["name"]),
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=timestamp,
                                start_time=start_time,
                            )
                        )

            except Exception as e:
                print("[STAKE PARSE ERROR]", e)
                continue

        return results
