from typing import Dict, List, Tuple

def make_key(item: Dict) -> Tuple:
    return (item.get("event_id"), item.get("bookmaker"), item.get("market"), item.get("selection"))

def dedupe_add(store: List[Dict], new_items: List[Dict]) -> int:
    existing = {make_key(i): i for i in store}
    added = 0
    for it in new_items:
        k = make_key(it)
        if k not in existing:
            store.append(it)
            existing[k] = it
            added += 1
        else:
            if existing[k].get("odds") != it.get("odds"):
                existing[k].update(it)
    return added
