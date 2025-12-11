from typing import List, Dict

def detect_surebets(odds_list: List[Dict], min_profit_pct: float = 0.1) -> List[Dict]:
    """
    Agrupa por (home, away, start_time, league).
    Calcula o melhor odd por selection (entre bookmakers).
    Se sum(1/odd_best) < 1 => surebet, profit_pct = (1 - sum_inv) * 100.
    """
    games = {}
    for o in odds_list:
        key = (o.get("home_team"), o.get("away_team"), o.get("start_time"), o.get("league"))
        games.setdefault(key, []).append(o)

    results = []
    for key, offers in games.items():
        best = {}
        for o in offers:
            sel = o.get("selection")
            if sel not in best or o.get("odds", 0) > best[sel]["odds"]:
                best[sel] = o
        if len(best) < 2:
            continue
        inv_sum = sum(1.0 / b["odds"] for b in best.values())
        if inv_sum < 1.0:
            profit_pct = (1.0 - inv_sum) * 100.0
            if profit_pct >= min_profit_pct:
                results.append({
                    "home_team": key[0],
                    "away_team": key[1],
                    "start_time": key[2],
                    "league": key[3],
                    "profit_pct": profit_pct,
                    "best_odds": list(best.values())
                })
    return results
