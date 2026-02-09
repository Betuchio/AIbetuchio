"""Value Bet-ების დეტექცია."""
import pandas as pd
import numpy as np

from src.config import MIN_EDGE_THRESHOLD
from src.utils.helpers import implied_probabilities, kelly_fraction
from src.utils.logger import get_logger

log = get_logger(__name__)


def find_value_bets(predictions: pd.DataFrame,
                    min_edge: float = MIN_EDGE_THRESHOLD) -> pd.DataFrame:
    """Value bet-ების პოვნა პროგნოზებიდან.

    Value bet = მოდელის ალბათობა > ბუკმეკერის ნაგულისხმევი ალბათობა + edge threshold
    """
    if predictions.empty:
        return pd.DataFrame()

    value_bets = []

    for _, row in predictions.iterrows():
        odds_h = row.get("B365H", 0)
        odds_d = row.get("B365D", 0)
        odds_a = row.get("B365A", 0)

        if not all([odds_h, odds_d, odds_a]):
            continue

        impl_h, impl_d, impl_a = implied_probabilities(odds_h, odds_d, odds_a)

        # მოდელის ალბათობები
        model_h = row.get("prob_H", 0)
        model_d = row.get("prob_D", 0)
        model_a = row.get("prob_A", 0)

        # თითოეული შედეგისთვის edge-ის გამოთვლა
        bets_to_check = [
            ("H", "Home Win", model_h, impl_h, odds_h),
            ("D", "Draw", model_d, impl_d, odds_d),
            ("A", "Away Win", model_a, impl_a, odds_a),
        ]

        for result, label, model_prob, impl_prob, odds in bets_to_check:
            edge = model_prob - impl_prob

            if edge > min_edge:
                kelly = kelly_fraction(edge, odds)
                expected_value = (model_prob * odds) - 1

                value_bets.append({
                    "date": str(row.get("Date", "")),
                    "home_team": row.get("HomeTeam", ""),
                    "away_team": row.get("AwayTeam", ""),
                    "division": row.get("Div", ""),
                    "bet_type": label,
                    "bet_result": result,
                    "odds": odds,
                    "model_prob": round(model_prob, 4),
                    "implied_prob": round(impl_prob, 4),
                    "edge": round(edge, 4),
                    "edge_pct": round(edge * 100, 2),
                    "kelly_fraction": round(kelly, 4),
                    "kelly_pct": round(kelly * 100, 2),
                    "expected_value": round(expected_value, 4),
                    "confidence": float(row.get("confidence", 0)),
                    "actual_result": row.get("FTR", ""),
                })

    if not value_bets:
        log.info("Value bet-ები ვერ მოიძებნა")
        return pd.DataFrame()

    vb_df = pd.DataFrame(value_bets)
    vb_df = vb_df.sort_values("edge", ascending=False).reset_index(drop=True)

    log.info(f"ნაპოვნია {len(vb_df)} value bet (min edge: {min_edge*100:.1f}%)")
    return vb_df


def analyze_value_bets_performance(value_bets: pd.DataFrame) -> dict:
    """Value bet-ების ისტორიული წარმადობის ანალიზი."""
    if value_bets.empty or "actual_result" not in value_bets.columns:
        return {}

    # მხოლოდ ის მატჩები სადაც შედეგი ცნობილია
    completed = value_bets[value_bets["actual_result"].isin(["H", "D", "A"])].copy()
    if completed.empty:
        return {}

    completed["is_correct"] = completed["bet_result"] == completed["actual_result"]
    completed["profit"] = completed.apply(
        lambda r: (r["odds"] - 1) if r["is_correct"] else -1, axis=1
    )

    total_bets = len(completed)
    wins = completed["is_correct"].sum()
    win_rate = wins / total_bets if total_bets > 0 else 0
    total_profit = completed["profit"].sum()
    roi = (total_profit / total_bets) * 100 if total_bets > 0 else 0
    avg_odds = completed["odds"].mean()
    avg_edge = completed["edge"].mean()

    return {
        "total_bets": total_bets,
        "wins": int(wins),
        "losses": total_bets - int(wins),
        "win_rate": round(win_rate * 100, 2),
        "total_profit": round(total_profit, 2),
        "roi": round(roi, 2),
        "avg_odds": round(avg_odds, 2),
        "avg_edge": round(avg_edge * 100, 2),
    }
