import unicodedata
import re

# FIXES que você já tinha
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
    "moneyline": "1x2",
    "over under": "over_under",
    "total": "over_under",
    "totals": "over_under",
    "handicap": "handicap",
    "asian handicap": "handicap",
    "btts": "btts",
    "both teams to score": "btts",
}

SELECTION_FIX = {
    "home": "1",
    "away": "2",
    "draw": "x",
    "empate": "x",
    "casa": "1",
    "fora": "2",
    "sim": "yes",
    "nao": "no",
    "não": "no",
}

# ---------------------------
# Normalização base
# ---------------------------
def _clean(text: str) -> str:
    if not text:
        return ""

    text = text.lower().strip()

    # remover acentos
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("utf-8")

    # padronizar
    text = text.replace("-", " ").replace("_", " ")
    text = re.sub(r"\s+", " ", text)

    return text


# ---------------------------
# Times
# ---------------------------
def clean_team_name(name: str) -> str:
    key = _clean(name)
    return TEAM_FIX.get(key, key).title()


# ---------------------------
# Ligas
# ---------------------------
def clean_league_name(name: str) -> str:
    key = _clean(name)
    return LEAGUE_FIX.get(key, key)


# ---------------------------
# Mercados
# ---------------------------
def clean_market_name(name: str) -> str:
    key = _clean(name)

    # tentamos fix direct
    if key in MARKET_FIX:
        return MARKET_FIX[key]

    # padrões comuns
    if "over" in key or "under" in key:
        return "over_under"

    if "handicap" in key:
        return "handicap"

    if "btts" in key or "both teams" in key:
        return "btts"

    return key


# ---------------------------
# Seleções (a parte mais importante!)
# ---------------------------
def clean_selection_name(name: str) -> str:
    s = _clean(name)

    # fixes diretos
    if s in SELECTION_FIX:
        return SELECTION_FIX[s]

    # OVER/UNDER ex: "over 2.5"
    ou = re.match(r"(over|under)\s*([0-9]+\.?[0-9]*)", s)
    if ou:
        return f"{ou.group(1)}_{ou.group(2)}"

    # HANDICAP ex: "+1.5", "-2", "ah -1"
    hcp = re.match(r"(ah\s*)?([+-]?[0-9]+\.?[0-9]*)", s)
    if hcp:
        return hcp.group(2)

    return s
