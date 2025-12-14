import aiohttp
import asyncio
import uuid
from datetime import datetime
from typing import List

from scrapers.base import BaseScraper
from models.odds import Odds


class StakeScraper(BaseScraper):
    name = "stake"

    async def fetch_upcoming(self, days_ahead: int = 7) -> List[Odds]:
        """
        Scraper real usando a API pública da Stake.
        Coleta múltiplos mercados para criar oportunidade de surebet:
        - 1x2
        - Dupla Chance
        - Over/Under 2.5
        - Ambas Marcam
        - Handicap Asiático (quando disponível)
        """
        out: List[Odds] = []

        url = (
            "https://api.stake.com/sports/events?"
            "sport=soccer&limit=100&marketType=match_odds,totals,team_totals,"
            "double_chance,both_teams_to_score,asian_handicap"
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=20) as resp:
                    data = await resp.json()

            events = data.get("events", [])
            for ev in events:
                try:
                    home = ev["homeTeam"]["name"]
                    away = ev["awayTeam"]["name"]
                    league = ev["competition"]["name"]
                    markets = ev.get("markets", [])

                    # -------------------------
                    # MERCADO 1 — 1x2
                    # -------------------------
                    m_1x2 = next((m for m in markets if m["key"] == "match_odds"), None)
                    if m_1x2:
                        outs = m_1x2.get("outcomes", [])
                        if len(outs) >= 3:
                            odd_home = float(outs[0]["price"])
                            odd_draw = float(outs[1]["price"])
                            odd_away = float(outs[2]["price"])

                            out.extend([
                                Odds(
                                    event_id=str(uuid.uuid4()),
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    market="1x2",
                                    selection="home",
                                    odds=odd_home,
                                    bookmaker=self.name,
                                    timestamp=datetime.utcnow().isoformat() + "Z",
                                ),
                                Odds(
                                    event_id=str(uuid.uuid4()),
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    market="1x2",
                                    selection="draw",
                                    odds=odd_draw,
                                    bookmaker=self.name,
                                    timestamp=datetime.utcnow().isoformat() + "Z",
                                ),
                                Odds(
                                    event_id=str(uuid.uuid4()),
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    market="1x2",
                                    selection="away",
                                    odds=odd_away,
                                    bookmaker=self.name,
                                    timestamp=datetime.utcnow().isoformat() + "Z",
                                ),
                            ])

                    # -------------------------
                    # MERCADO 2 — DUPLA CHANCE
                    # -------------------------
                    m_dc = next((m for m in markets if m["key"] == "double_chance"), None)
                    if m_dc:
                        for outcome in m_dc.get("outcomes", []):
                            out.append(
                                Odds(
                                    event_id=str(uuid.uuid4()),
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    market="double_chance",
                                    selection=outcome["name"],  # "1X", "X2", "12"
                                    odds=float(outcome["price"]),
                                    bookmaker=self.name,
                                    timestamp=datetime.utcnow().isoformat() + "Z",
                                )
                            )

                    # -------------------------
                    # MERCADO 3 — OVER / UNDER 2.5
                    # -------------------------
                    m_ou = next((m for m in markets if m["key"] == "totals"), None)
                    if m_ou:
                        for outcome in m_ou.get("outcomes", []):
                            # exemplo: "over 2.5", "under 2.5"
                            out.append(
                                Odds(
                                    event_id=str(uuid.uuid4()),
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    market="over_under",
                                    selection=outcome["name"],
                                    odds=float(outcome["price"]),
                                    bookmaker=self.name,
                                    timestamp=datetime.utcnow().isoformat() + "Z",
                                )
                            )

                    # -------------------------
                    # MERCADO 4 — AMBAS MARCAM
                    # -------------------------
                    m_btts = next((m for m in markets if m["key"] == "both_teams_to_score"), None)
                    if m_btts:
                        for outcome in m_btts.get("outcomes", []):
                            out.append(
                                Odds(
                                    event_id=str(uuid.uuid4()),
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    market="both_teams_score",
                                    selection=outcome["name"],  # "yes" / "no"
                                    odds=float(outcome["price"]),
                                    bookmaker=self.name,
                                    timestamp=datetime.utcnow().isoformat() + "Z",
                                )
                            )

                    # -------------------------
                    # MERCADO 5 — HANDICAP ASIÁTICO
                    # -------------------------
                    m_ah = next((m for m in markets if m["key"] == "asian_handicap"), None)
                    if m_ah:
                        for outcome in m_ah.get("outcomes", []):
                            out.append(
                                Odds(
                                    event_id=str(uuid.uuid4()),
                                    home_team=home,
                                    away_team=away,
                                    league=league,
                                    market="asian_handicap",
                                    selection=outcome["name"],  # exemplo "-1.5", "+0.25"
                                    odds=float(outcome["price"]),
                                    bookmaker=self.name,
                                    timestamp=datetime.utcnow().isoformat() + "Z",
                                )
                            )

                except Exception:
                    continue

        except Exception as e:
            print(f"[StakeScraper] erro: {e}")

        return out
