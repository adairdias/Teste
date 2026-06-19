"""
Fetches live odds from The Odds API (aggregates Betfair, Pinnacle, Bet365, etc.)
Docs: https://the-odds-api.com/liveapi/guides/v4/
"""

import httpx
from typing import Any

BASE_URL = "https://api.the-odds-api.com/v4"

# Sports available on The Odds API that include Betfair
SUPPORTED_SPORTS = [
    {"key": "tennis_atp_french_open", "title": "ATP French Open"},
    {"key": "tennis_wta_french_open", "title": "WTA French Open"},
    {"key": "tennis_atp_wimbledon", "title": "ATP Wimbledon"},
    {"key": "tennis_atp_us_open", "title": "ATP US Open"},
    {"key": "soccer_brazil_campeonato", "title": "Brasileirão Série A"},
    {"key": "soccer_conmebol_copa_libertadores", "title": "Copa Libertadores"},
    {"key": "soccer_epl", "title": "Premier League"},
    {"key": "basketball_nba", "title": "NBA"},
    {"key": "soccer_brazil_serie_b", "title": "Brasileirão Série B"},
]

# Bookmakers that commonly have exploitable odds differences
TARGET_BOOKMAKERS = [
    "betfair_ex_eu",   # Betfair Exchange (Europe) - often best for lay
    "betfair_ex_best", # Betfair best available
    "pinnacle",        # Pinnacle - high limits, low margin
    "bet365",
    "unibet",
    "betway",
    "1xbet",
    "draftkings",
    "fanduel",
    "betano",
]


async def fetch_sports(api_key: str) -> list[dict]:
    """Returns list of active sports from the API."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{BASE_URL}/sports",
            params={"apiKey": api_key, "all": "false"},
        )
        resp.raise_for_status()
        return resp.json()


async def fetch_odds(
    api_key: str,
    sport_key: str,
    regions: str = "eu,uk",
    markets: str = "h2h",
    bookmakers: str | None = None,
) -> list[dict]:
    """
    Fetches odds for all events of a given sport.
    regions: 'eu' for European bookmakers, 'uk' for UK, 'us' for US
    markets: 'h2h' (head to head / moneyline), 'spreads', 'totals'
    """
    params: dict[str, Any] = {
        "apiKey": api_key,
        "regions": regions,
        "markets": markets,
        "oddsFormat": "decimal",
    }
    if bookmakers:
        params["bookmakers"] = bookmakers

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{BASE_URL}/sports/{sport_key}/odds",
            params=params,
        )
        resp.raise_for_status()
        return resp.json()


def parse_odds_to_bookmaker_map(
    event: dict,
) -> dict[str, dict[str, float]]:
    """
    Converts raw API event data to:
    { "Bookmaker Name": { "Outcome Name": odds_float, ... }, ... }
    """
    result: dict[str, dict[str, float]] = {}
    for bookmaker in event.get("bookmakers", []):
        name = bookmaker["title"]
        for market in bookmaker.get("markets", []):
            if market["key"] != "h2h":
                continue
            result[name] = {
                outcome["name"]: outcome["price"]
                for outcome in market["outcomes"]
            }
    return result


def get_demo_events() -> list[dict]:
    """
    Returns demo events with realistic odds for testing without an API key.
    Includes some artificial arbitrage opportunities to demonstrate the tool.
    """
    return [
        {
            "id": "demo_tennis_1",
            "sport_key": "tennis_atp",
            "sport_title": "ATP Tennis",
            "home_team": "Carlos Alcaraz",
            "away_team": "Jannik Sinner",
            "commence_time": "2026-06-20T14:00:00Z",
            "bookmakers": [
                {
                    "title": "Betfair Exchange",
                    "markets": [{"key": "h2h", "outcomes": [
                        {"name": "Carlos Alcaraz", "price": 2.10},
                        {"name": "Jannik Sinner", "price": 1.80},
                    ]}],
                },
                {
                    "title": "Pinnacle",
                    "markets": [{"key": "h2h", "outcomes": [
                        {"name": "Carlos Alcaraz", "price": 1.95},
                        {"name": "Jannik Sinner", "price": 2.20},
                    ]}],
                },
                {
                    "title": "Bet365",
                    "markets": [{"key": "h2h", "outcomes": [
                        {"name": "Carlos Alcaraz", "price": 2.00},
                        {"name": "Jannik Sinner", "price": 1.90},
                    ]}],
                },
            ],
        },
        {
            "id": "demo_soccer_1",
            "sport_key": "soccer_brazil_campeonato",
            "sport_title": "Brasileirão Série A",
            "home_team": "Flamengo",
            "away_team": "Palmeiras",
            "commence_time": "2026-06-21T20:00:00Z",
            "bookmakers": [
                {
                    "title": "Betfair Exchange",
                    "markets": [{"key": "h2h", "outcomes": [
                        {"name": "Flamengo", "price": 2.60},
                        {"name": "Draw", "price": 3.10},
                        {"name": "Palmeiras", "price": 2.80},
                    ]}],
                },
                {
                    "title": "Bet365",
                    "markets": [{"key": "h2h", "outcomes": [
                        {"name": "Flamengo", "price": 2.40},
                        {"name": "Draw", "price": 3.50},
                        {"name": "Palmeiras", "price": 2.70},
                    ]}],
                },
                {
                    "title": "Pinnacle",
                    "markets": [{"key": "h2h", "outcomes": [
                        {"name": "Flamengo", "price": 2.55},
                        {"name": "Draw", "price": 3.20},
                        {"name": "Palmeiras", "price": 3.10},
                    ]}],
                },
            ],
        },
        {
            "id": "demo_tennis_2",
            "sport_key": "tennis_wta",
            "sport_title": "WTA Tennis",
            "home_team": "Iga Swiatek",
            "away_team": "Aryna Sabalenka",
            "commence_time": "2026-06-20T16:30:00Z",
            "bookmakers": [
                {
                    "title": "Betfair Exchange",
                    "markets": [{"key": "h2h", "outcomes": [
                        {"name": "Iga Swiatek", "price": 1.65},
                        {"name": "Aryna Sabalenka", "price": 2.40},
                    ]}],
                },
                {
                    "title": "Unibet",
                    "markets": [{"key": "h2h", "outcomes": [
                        {"name": "Iga Swiatek", "price": 1.72},
                        {"name": "Aryna Sabalenka", "price": 2.25},
                    ]}],
                },
            ],
        },
        {
            "id": "demo_nba_1",
            "sport_key": "basketball_nba",
            "sport_title": "NBA",
            "home_team": "Boston Celtics",
            "away_team": "Golden State Warriors",
            "commence_time": "2026-06-22T01:00:00Z",
            "bookmakers": [
                {
                    "title": "Betfair Exchange",
                    "markets": [{"key": "h2h", "outcomes": [
                        {"name": "Boston Celtics", "price": 1.85},
                        {"name": "Golden State Warriors", "price": 2.10},
                    ]}],
                },
                {
                    "title": "Pinnacle",
                    "markets": [{"key": "h2h", "outcomes": [
                        {"name": "Boston Celtics", "price": 1.90},
                        {"name": "Golden State Warriors", "price": 2.05},
                    ]}],
                },
                {
                    "title": "DraftKings",
                    "markets": [{"key": "h2h", "outcomes": [
                        {"name": "Boston Celtics", "price": 1.87},
                        {"name": "Golden State Warriors", "price": 2.15},
                    ]}],
                },
            ],
        },
    ]
