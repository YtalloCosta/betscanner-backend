import unidecode

# ===========================
# 1) NORMALIZAÇÃO DE TIMES
# ===========================

TEAM_FIX = {
    "sao paulo": "São Paulo",
    "spfc": "São Paulo",
    "sao paulo sp": "São Paulo",
    "s paulo": "São Paulo",

    "palmeiras": "Palmeiras",
    "sep": "Palmeiras",

    "vasco da gama": "Vasco",
    "vasco": "Vasco",

    "flamengo": "Flamengo",
    "cr flamengo": "Flamengo",

    "fluminense": "Fluminense",
    "flu": "Fluminense",

    "corinthians": "Corinthians",
    "sccp": "Corinthians",

    "gremio": "Grêmio",
    "gremio fbpa": "Grêmio",

    "internacional": "Internacional",
    "sport club internacional": "Internacional",
}

BAD_TEAM_WORDS = [
    "fc", "f.c", "f.c.", "cf", "c.f.", "futebol clube",
    "futebol", "clube", "ec", "e.c.", "sc", "s.c.",
    "-sp", "-rj", "-rs", "-mg"
]

def clean_team_name(name: str) -> str:
    if not name:
        return name

    n = unidecode.unidecode(name).lower().strip()
    for bad in BAD_TEAM_WORDS:
        n = n.replace(bad, "").strip()
    n = " ".join(n.split())
    if n in TEAM_FIX:
        return TEAM_FIX[n]
    return n.title()



# ===========================
# 2) NORMALIZAÇÃO DE LIGAS
# ===========================

LEAGUE_FIX = {
    # Brasil
    "brazil serie a": "Brasileirão Série A",
    "brasileirao a": "Brasileirão Série A",
    "serie a brazil": "Brasileirão Série A",
    
    "brazil serie b": "Brasileirão Série B",

    # Inglaterra
    "premier league": "Premier League",
    "england premier league": "Premier League",

    # Espanha
    "la liga": "La Liga",
    "laliga": "La Liga",
    "spanish primera division": "La Liga",

    # Itália
    "serie a": "Serie A (Itália)",
    "italy serie a": "Serie A (Itália)",

    # Alemanha
    "bundesliga": "Bundesliga",
}

BAD_LEAGUE_WORDS = [
    " - men", " - women", "(br)", "(bra)", "(eng)", "(ita)"
]

def clean_league_name(league: str) -> str:
    if not league:
        return league

    n = unidecode.unidecode(league).lower().strip()

    for bad in BAD_LEAGUE_WORDS:
        n = n.replace(bad, "")

    n = " ".join(n.split())

    if n in LEAGUE_FIX:
        return LEAGUE_FIX[n]

    return n.title()



# ===========================
# 3) NORMALIZAÇÃO DE MERCADOS
# ===========================

MARKET_FIX = {
    "1x2": "match_result",
    "match_result": "match_result",
    "moneyline": "match_result",
    "result": "match_result",

    "double_chance": "double_chance",
    "dc": "double_chance",

    "over_under": "over_under",
    "totals": "over_under",

    "btts": "both_teams_score",
    "both_teams_score": "both_teams_score",
    "both_teams_to_score": "both_teams_score",

    "asian_handicap": "asian_handicap",
    "handicap_asian": "asian_handicap",
    "spread": "asian_handicap",
}

def clean_market_name(market: str) -> str:
    if not market:
        return market
    m = unidecode.unidecode(market).lower().strip()
    return MARKET_FIX.get(m, m)



# ===========================
# 4) NORMALIZAÇÃO DE SELEÇÕES
# ===========================

SELECTION_FIX = {
    "home": "home",
    "1": "home",
    "team1": "home",

    "draw":
