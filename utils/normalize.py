import unidecode

# Dicionário de normalização manual (muito importante)
TEAM_FIX = {
    "sao paulo": "São Paulo",
    "spfc": "São Paulo",
    "sao paulo sp": "São Paulo",

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
    "sc internacional": "Internacional",

    # Você pode adicionar outros aqui
}


def clean_team_name(name: str) -> str:
    """Padroniza nome de times para evitar duplicidade entre casas."""
    if not name:
        return name

    # remove acentos
    n = unidecode.unidecode(name)

    # caixa baixa
    n = n.lower().strip()

    # remove siglas comuns
    BAD_WORDS = [
        "fc", "f.c", "f.c.", "cf", "c.f.", "futebol clube",
        "futebol", "clube", "ec", "e.c.", "sc", "s.c.", "-sp", "-rj"
    ]

    for bad in BAD_WORDS:
        n = n.replace(bad, "").strip()

    # remove múltiplos espaços
    n = " ".join(n.split())

    # aplica dicionário manual
    if n in TEAM_FIX:
        return TEAM_FIX[n]

    # capitalização padrão (São Paulo → Sao Paulo → São Paulo ficaria sem acento, mas ajustado no TEAM_FIX)
    return n.title()
