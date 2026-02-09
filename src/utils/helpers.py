import pandas as pd
from datetime import datetime, timedelta


def parse_date(date_str: str) -> datetime:
    """სხვადასხვა ფორმატის თარიღის პარსინგი."""
    formats = ["%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(str(date_str).strip(), fmt)
        except (ValueError, TypeError):
            continue
    return pd.NaT


def odds_to_probability(odds: float) -> float:
    """კოეფიციენტის ალბათობაში გარდაქმნა."""
    if odds and odds > 0:
        return 1.0 / odds
    return 0.0


def normalize_probabilities(prob_h: float, prob_d: float, prob_a: float) -> tuple:
    """ალბათობების ნორმალიზება (margin-ის მოხსნა) რომ ჯამი = 1."""
    total = prob_h + prob_d + prob_a
    if total > 0:
        return prob_h / total, prob_d / total, prob_a / total
    return 0.33, 0.34, 0.33


def implied_probabilities(odds_h: float, odds_d: float, odds_a: float) -> tuple:
    """კოეფიციენტებიდან ნორმალიზებული ალბათობების გამოთვლა."""
    p_h = odds_to_probability(odds_h)
    p_d = odds_to_probability(odds_d)
    p_a = odds_to_probability(odds_a)
    return normalize_probabilities(p_h, p_d, p_a)


def kelly_fraction(edge: float, odds: float) -> float:
    """Kelly criterion-ით ფსონის ზომის გამოთვლა."""
    if odds <= 1 or edge <= 0:
        return 0.0
    fraction = edge / (odds - 1)
    return min(fraction, 0.05)  # მაქსიმუმ 5% ბანკროლის


def result_to_label(ftr: str) -> str:
    """FTR (Full Time Result) -> წაკითხვადი ლეიბელი."""
    mapping = {"H": "Home Win", "D": "Draw", "A": "Away Win"}
    return mapping.get(str(ftr).upper(), "Unknown")


def season_to_years(season_code: str) -> str:
    """სეზონის კოდიდან წლების სტრინგი. 2324 -> 2023/24"""
    if len(season_code) == 4:
        y1 = int("20" + season_code[:2])
        y2 = season_code[2:]
        return f"{y1}/{y2}"
    return season_code


def get_today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def get_weekend_dates() -> list:
    """შაბათ-კვირის თარიღების სია."""
    today = datetime.now()
    saturday = today + timedelta(days=(5 - today.weekday()) % 7)
    sunday = saturday + timedelta(days=1)
    return [saturday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")]
