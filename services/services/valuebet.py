from typing import List, Dict

def detect_valuebets(odds_list: List[Dict], min_ev_pct: float = 2.0) -> List[Dict]:
    results = []
    for o in odds_list:
        if o.get("odds", 0) >= 2.0:
            implied = 1.0 / o.get("odds", 1.0)
            ev = (0.5 - implied) * 100.0
            if ev >= min_ev_pct:
                results.append({
                    "home_team": o.get("home_team"),
                    "away_team": o.get("away_team"),
                    "league": o.get("league"),
                    "expected_value": ev,
                    "odds": o.get("odds"),
                    "bookmaker": o.get("bookmaker"),
                    "market": o.get("market"),
                    "selection": o.get("selection")
                })
    return results
