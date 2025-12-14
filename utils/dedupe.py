from typing import List, Dict
from datetime import datetime

def odds_key(odd: Dict) -> str:
    """
    Define o que é considerado duplicado:
    - home team
    - away team
    - league
    - market
    - selection
    - bookmaker
    """
    return (
        f"{odd.get('home_team','')}|"
        f"{odd.get('away_team','')}|"
        f"{odd.get('league','')}|"
        f"{odd.get('market','')}|"
        f"{odd.get('selection','')}|"
        f"{odd.get('bookmaker','')}"
    )


def dedupe_add(store: List[Dict], new_items: List[Dict], keep="highest") -> int:
    """
    Remove duplicatas ao adicionar novas odds:

    keep:
      - 'highest': mantém a odd com maior preço
      - 'latest': mantém a odd mais recente (timestamp)
    """

    index = {odds_key(item): item for item in store}
    added = 0

    for odd in new_items:
        key = odds_key(odd)

        if key not in index:
            index[key] = odd
            added += 1
            continue

        existing = index[key]

        # comparar odds
        if keep == "highest":
            if float(odd.get("odds", 0)) > float(existing.get("odds", 0)):
                index[key] = odd

        elif keep == "latest":
            if odd.get("timestamp", "") > existing.get("timestamp", ""):
                index[key] = odd

    # Atualiza store em memória
    store.clear()
    store.extend(index.values())

    return added
