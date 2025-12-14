from typing import List, Dict
from models.odds import Odds


def dedupe_odds(odds_list: List[Odds], keep="highest") -> List[Odds]:
    """
    Remove odds duplicadas.
    
    Duplicação é definida por:
    - home_team
    - away_team
    - league
    - market
    - selection
    - bookmaker

    keep:
        "highest" → mantém a odd mais alta
        "latest" → mantém a odd mais recente
    """

    unique: Dict[str, Odds] = {}

    for odd in odds_list:
        key = f"{odd.home_team}|{odd.away_team}|{odd.league}|{odd.market}|{odd.selection}|{odd.bookmaker}"

        # se não existe ainda → guarda
        if key not in unique:
            unique[key] = odd
            continue

        # já existe → decidir quem manter
        existing = unique[key]

        if keep == "highest":
            if odd.odds > existing.odds:
                unique[key] = odd

        elif keep == "latest":
            if odd.timestamp > existing.timestamp:
                unique[key] = odd

    return list(unique.values())
