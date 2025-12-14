# utils/normalize.py

TEAM_FIX = {
    "manchester united": "man united",
    "manchester city": "man city",
    "internacional": "inter",
    "sport club internacional": "inter",
    "psg": "paris sg",
    "bayern munich": "bayern",
    "atletico mg": "atlético-mg",
    "atletico mineiro": "atlético-mg",
    "flamengo rj": "flamengo",
    "vasco da gama": "vasco",
    "botafogo rj": "botafogo",
    "gremio": "grêmio",
    "palmeiras sp": "palmeiras",
}

LEAGUE_FIX = {
    "premier league": "inglaterra - premier league",
    "la liga": "espanha - la liga",
    "bundesliga": "alemanha - bundesliga",
    "serie a": "itália - série a",
    "ligue 1": "frança - ligue 1",
    "campeonato brasileiro": "brasil - brasileirao",
    "brasileirao série a": "brasil - brasileirao",
}

MARKET_FIX = {
    "1x2": "1x2",
    "match winner": "1x2",
    "result": "1x2",
    "moneyline": "1x2"
}

SELECTION_FIX = {
    "home": "home",
    "away": "away",
    "draw": "draw",
    "empate": "draw",
    "casa": "home",
    "fora": "away",
}

def clean_name(text: str) -> str:
    if not text:
        return ""
    return (
        text.lower()
        .replace("-", " ")
        .replace("_", " ")
        .strip()
    )

def clean_team_name(name: str) -> str:
    key = clean_name(name)
    return TEAM_FIX.get(key, key)

def clean_league_name(name: str) -> str:
    key = clean_name(name)
    return LEAGUE_FIX.get(key, key)

def clean_market_name(name: str) -> str:
    key = clean_name(name)
    return MARKET_FIX.get(key, key)

def clean_selection_name(name: str) -> str:
    key = clean_name(name)
    return SELECTION_FIX.get(key, key)
