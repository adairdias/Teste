"""
Arbitrage Odds Finder - Backend API
Compares odds across Betfair and other bookmakers to find guaranteed profit opportunities.
"""

import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from pydantic import BaseModel

from odds_fetcher import (
    fetch_sports,
    fetch_odds,
    parse_odds_to_bookmaker_map,
    get_demo_events,
    SUPPORTED_SPORTS,
)
from arbitrage import check_arbitrage, ArbOpportunity

load_dotenv()

app = FastAPI(title="Arbitrage Odds Finder", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ArbBetOut(BaseModel):
    outcome: str
    bookmaker: str
    odds: float
    stake: float
    profit_if_wins: float


class ArbOpportunityOut(BaseModel):
    event_id: str
    sport: str
    home_team: str
    away_team: str
    commence_time: str
    bets: list[ArbBetOut]
    total_stake: float
    guaranteed_profit: float
    profit_percent: float
    arb_percent: float


def opportunity_to_out(opp: ArbOpportunity) -> ArbOpportunityOut:
    return ArbOpportunityOut(
        event_id=opp.event_id,
        sport=opp.sport,
        home_team=opp.home_team,
        away_team=opp.away_team,
        commence_time=opp.commence_time,
        bets=[ArbBetOut(**b.__dict__) for b in opp.bets],
        total_stake=opp.total_stake,
        guaranteed_profit=opp.guaranteed_profit,
        profit_percent=opp.profit_percent,
        arb_percent=opp.arb_percent,
    )


@app.get("/api/health")
async def health():
    api_key = os.getenv("ODDS_API_KEY", "")
    return {
        "status": "ok",
        "api_key_configured": bool(api_key and api_key != "your_key_here"),
        "mode": "live" if (api_key and api_key != "your_key_here") else "demo",
    }


@app.get("/api/sports")
async def list_sports():
    """List available sports to scan for arbitrage."""
    api_key = os.getenv("ODDS_API_KEY", "")
    if not api_key or api_key == "your_key_here":
        return {"sports": SUPPORTED_SPORTS, "mode": "demo"}
    try:
        sports = await fetch_sports(api_key)
        return {"sports": sports, "mode": "live"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch sports: {e}")


@app.get("/api/arbitrage", response_model=list[ArbOpportunityOut])
async def find_arbitrage(
    sport: str = Query(default="all", description="Sport key or 'all'"),
    stake: float = Query(default=100.0, ge=1.0, le=100000.0, description="Total stake in BRL"),
    min_profit: float = Query(default=0.0, description="Minimum profit % filter"),
):
    """
    Scan events and return arbitrage opportunities.
    In demo mode (no API key) returns realistic sample data.
    """
    api_key = os.getenv("ODDS_API_KEY", "")
    demo_mode = not api_key or api_key == "your_key_here"

    if demo_mode:
        events = get_demo_events()
        if sport != "all":
            events = [e for e in events if e.get("sport_key") == sport]
    else:
        sports_to_scan = (
            [sport] if sport != "all"
            else [s["key"] for s in SUPPORTED_SPORTS]
        )
        events = []
        for sport_key in sports_to_scan:
            try:
                fetched = await fetch_odds(api_key, sport_key, regions="eu,uk")
                events.extend(fetched)
            except Exception:
                continue

    opportunities: list[ArbOpportunityOut] = []

    for event in events:
        bookmaker_map = parse_odds_to_bookmaker_map(event)
        opp = check_arbitrage(
            event_id=event.get("id", ""),
            sport=event.get("sport_title", event.get("sport_key", "")),
            home_team=event.get("home_team", ""),
            away_team=event.get("away_team", ""),
            commence_time=event.get("commence_time", ""),
            outcomes_by_bookmaker=bookmaker_map,
            total_stake=stake,
        )
        if opp and opp.profit_percent >= min_profit:
            opportunities.append(opportunity_to_out(opp))

    opportunities.sort(key=lambda x: x.profit_percent, reverse=True)
    return opportunities


@app.get("/api/simulate")
async def simulate(
    odds_a: float = Query(..., description="Odds for outcome A"),
    odds_b: float = Query(..., description="Odds for outcome B"),
    odds_c: float = Query(default=0.0, description="Odds for outcome C (optional, e.g. draw)"),
    stake: float = Query(default=100.0, description="Total stake"),
):
    """
    Simulate a custom arbitrage scenario with provided odds.
    Useful for manually checking if a situation is profitable.
    """
    outcomes: dict[str, dict[str, float]] = {
        "Bookmaker A": {"Resultado A": odds_a},
        "Bookmaker B": {"Resultado B": odds_b},
    }
    if odds_c > 1.0:
        outcomes["Bookmaker C"] = {"Empate": odds_c}

    opp = check_arbitrage(
        event_id="simulation",
        sport="Simulação",
        home_team="Time A",
        away_team="Time B",
        commence_time="",
        outcomes_by_bookmaker=outcomes,
        total_stake=stake,
    )

    if opp:
        return {
            "is_arbitrage": True,
            "profit_percent": opp.profit_percent,
            "guaranteed_profit": opp.guaranteed_profit,
            "bets": [b.__dict__ for b in opp.bets],
            "arb_percent": opp.arb_percent,
            "explanation": (
                f"Apostando R${stake:.2f} total, você ganha R${opp.guaranteed_profit:.2f} "
                f"({opp.profit_percent:.2f}%) independente do resultado."
            ),
        }
    else:
        implied = 1 / odds_a + 1 / odds_b + (1 / odds_c if odds_c > 1.0 else 0)
        return {
            "is_arbitrage": False,
            "implied_probability_sum": round(implied * 100, 2),
            "margin": round((implied - 1) * 100, 2),
            "explanation": (
                f"Não há arbitragem. A margem da banca é {(implied - 1) * 100:.2f}%. "
                f"Para arbitragem, a soma das probabilidades implícitas precisa ser < 100%."
            ),
        }


# Serve frontend
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_path, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
