"""
Arbitrage calculation engine.

Arbitrage exists when sum of (1/best_odds_per_outcome) < 1.
Example: odds 2.1 and 2.2 → 1/2.1 + 1/2.2 = 0.476 + 0.455 = 0.931 → 6.9% profit
"""

from dataclasses import dataclass


@dataclass
class ArbBet:
    outcome: str
    bookmaker: str
    odds: float
    stake: float
    profit_if_wins: float


@dataclass
class ArbOpportunity:
    event_id: str
    sport: str
    home_team: str
    away_team: str
    commence_time: str
    bets: list[ArbBet]
    total_stake: float
    guaranteed_profit: float
    profit_percent: float
    arb_percent: float  # sum of implied probs (< 100% = arb)


def find_best_odds(outcomes_by_bookmaker: dict[str, dict[str, float]]) -> dict[str, tuple[str, float]]:
    """For each outcome, find the bookmaker offering the highest odds."""
    best: dict[str, tuple[str, float]] = {}
    for bookmaker, outcomes in outcomes_by_bookmaker.items():
        for outcome, odds in outcomes.items():
            if outcome not in best or odds > best[outcome][1]:
                best[outcome] = (bookmaker, odds)
    return best


def calculate_stakes(best_odds: dict[str, tuple[str, float]], total_stake: float) -> list[ArbBet]:
    """
    Calculate how much to bet on each outcome so that all returns are equal.

    Formula: stake_i = total_stake * (1/odds_i) / sum(1/odds_j)
    This guarantees equal return regardless of which outcome occurs.
    """
    outcomes = list(best_odds.items())
    implied_probs = {name: 1 / odds for name, (_, odds) in best_odds.items()}
    total_implied = sum(implied_probs.values())

    bets = []
    for outcome, (bookmaker, odds) in best_odds.items():
        stake = total_stake * (implied_probs[outcome] / total_implied)
        profit_if_wins = stake * odds
        bets.append(ArbBet(
            outcome=outcome,
            bookmaker=bookmaker,
            odds=odds,
            stake=round(stake, 2),
            profit_if_wins=round(profit_if_wins, 2),
        ))
    return bets


def check_arbitrage(
    event_id: str,
    sport: str,
    home_team: str,
    away_team: str,
    commence_time: str,
    outcomes_by_bookmaker: dict[str, dict[str, float]],
    total_stake: float = 100.0,
) -> ArbOpportunity | None:
    """
    Returns an ArbOpportunity if profitable arbitrage exists, else None.
    Only considers H2H (2-outcome) and 3-way markets.
    """
    if not outcomes_by_bookmaker:
        return None

    best_odds = find_best_odds(outcomes_by_bookmaker)
    if len(best_odds) < 2:
        return None

    arb_percent = sum(1 / odds for _, odds in best_odds.values()) * 100

    if arb_percent >= 100:
        return None  # No arbitrage

    bets = calculate_stakes(best_odds, total_stake)
    guaranteed_return = bets[0].profit_if_wins  # all returns are equal
    guaranteed_profit = guaranteed_return - total_stake
    profit_percent = (guaranteed_profit / total_stake) * 100

    return ArbOpportunity(
        event_id=event_id,
        sport=sport,
        home_team=home_team,
        away_team=away_team,
        commence_time=commence_time,
        bets=bets,
        total_stake=round(total_stake, 2),
        guaranteed_profit=round(guaranteed_profit, 2),
        profit_percent=round(profit_percent, 2),
        arb_percent=round(arb_percent, 2),
    )
