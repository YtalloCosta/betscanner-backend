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
        "sport=soccer&limit=100&marketType="
        "match_odds,totals,double_chance,both_teams_to_score,asian_handicap"
    )

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        out: List[Odds] = []

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.API_URL, timeout=20) as resp:
                    data = await resp.json()
        except Exception as e:
            print(f"[Stake API ERROR] {e}")
            return out

        events = data.get("events", [])

        for ev in events:
            try:
                # ===============================
                # Dados base do evento
                # ===============================
                home = clean_team_name(ev["homeTeam"]["name"])
                away = clean_team_name(ev["awayTeam"]["name"])
                league = clean_league_name(ev["competition"]["name"])
                start_time = ev.get("startTime")

                # event_id consistente
                event_uid = str(
                    uuid.uuid5(uuid.NAMESPACE_DNS, f"stake-{home}-{away}-{start_time}")
                )

                timestamp = datetime.utcnow().isoformat() + "Z"

                markets = ev.get("markets", [])

                # ===============================
                # 1) MERCADO 1X2
                # ===============================
                m_1x2 = next((m for m in markets if m["key"] == "match_odds"), None)
                if m_1x2:
                    for sel in m_1x2.get("outcomes", []):
                        selection = clean_selection_name(sel["name"])
                        odds = float(sel["price"])

                        out.append(
                            Odds(
                                event_id=event_uid,
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

                # ===============================
                # 2) DUPLA CHANCE
                # ===============================
                m_dc = next((m for m in markets if m["key"] == "double_chance"), None)
                if m_dc:
                    for sel in m_dc.get("outcomes", []):
                        out.append(
                            Odds(
                                event_id=event_uid,
                                home_team=home,
                                away_team=away,
                                league=league,
                                sport="soccer",
                                market="double_chance",
                                selection=clean_selection_name(sel["name"]),
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=timestamp,
                                start_time=start_time,
                            )
                        )

                # ===============================
                # 3) OVER / UNDER (CORRETO)
                # ===============================
                m_ou = next((m for m in markets if m["key"] == "totals"), None)
                if m_ou:
                    for sel in m_ou.get("outcomes", []):
                        designation = sel.get("designation")  # over / under
                        points = sel.get("points")  # ex: 2.5
                        odds = float(sel["price"])

                        selection = f"{designation} {points}"

                        out.append(
                            Odds(
                                event_id=event_uid,
                                home_team=home,
                                away_team=away,
                                league=league,
                                sport="soccer",
                                market="over_under",
                                selection=selection,
                                odds=odds,
                                bookmaker=self.name,
                                timestamp=timestamp,
                                start_time=start_time,
                            )
                        )

                # ===============================
                # 4) AMBAS MARCAM
                # ===============================
                m_btts = next((m for m in markets if m["key"] == "both_teams_to_score"), None)
                if m_btts:
                    for sel in m_btts.get("outcomes", []):
                        out.append(
                            Odds(
                                event_id=event_uid,
                                home_team=home,
                                away_team=away,
                                league=league,
                                sport="soccer",
                                market="btts",
                                selection=clean_selection_name(sel["name"]),
                                odds=float(sel["price"]),
                                bookmaker=self.name,
                                timestamp=timestamp,
                                start_time=start_time,
                            )
                        )

                # ===============================
                # 5) HANDICAP ASIÁTICO
                # ===============================
                m_ah = next((m for m in markets if m["key"] == "asian_handicap"), None)
                if m_ah:
                    for sel in m_ah.get("outcomes", []):
                        points = sel.get("handicap")
                        odds = float(sel["price"])

                        selection = f"{points}"

                        out.append(
                            Odds(
                                event_id=event_uid,
                                home_team=home,
                                away_team=away,
                                league=league,
                                sport="soccer",
                                market="ah",
                                selection=selection,
                                odds=odds,
                                bookmaker=self.name,
                                timestamp=timestamp,
                                start_time=start_time,
                            )
                        )

            except Exception as e:
                print(f"[StakeScraper PARSE ERROR] {e}")
                continue

        return out
