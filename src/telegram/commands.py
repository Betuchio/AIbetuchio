"""Telegram ბრძანებების იმპლემენტაცია."""
import pandas as pd
from src.ml.predictor import Predictor
from src.ml.value_bets import find_value_bets
from src.data.db_manager import get_all_matches, get_bets
from src.config import LEAGUES
from src.telegram.formatters import (
    format_prediction, format_predictions_list, format_value_bets,
    format_standings, format_h2h, format_roi_summary,
)
from src.utils.helpers import get_today_str, get_weekend_dates
from src.utils.logger import get_logger

log = get_logger(__name__)

_predictor = None


def _get_predictor() -> Predictor:
    global _predictor
    if _predictor is None:
        _predictor = Predictor()
    return _predictor


def cmd_start() -> str:
    return (
        "⚽ *AIbetuchio-ში მოგესალმებით!*\n\n"
        "საფეხბურთო AI პროგნოზების სისტემა\n\n"
        "*ბრძანებები:*\n"
        "/today - დღევანდელი პროგნოზები\n"
        "/weekend - შაბათ-კვირის პროგნოზები\n"
        "/predict <გუნდი> - გუნდის პროგნოზი\n"
        "/valuebets - Value bet-ები\n"
        "/league <კოდი> - ლიგის ცხრილი\n"
        "/h2h <გუნდი1> vs <გუნდი2> - H2H\n"
        "/roi - ROI შეჯამება\n"
        "/leagues - ლიგების სია\n"
    )


def cmd_today() -> str:
    predictor = _get_predictor()
    if not predictor.is_ready():
        return "⚠️ მოდელი არ არის ჩატვირთული. გაწვრთნეთ ჯერ."

    predictions = predictor.get_latest_predictions(n=50)
    if predictions.empty:
        return "📊 დღევანდელი პროგნოზები ვერ მოიძებნა"

    today = get_today_str()
    today_preds = predictions[predictions["Date"] == today]

    if today_preds.empty:
        # თუ დღევანდელი არ არის, ბოლო 5 აჩვენე
        return "📊 დღეს მატჩები არ არის. ბოლო პროგნოზები:\n\n" + \
               format_predictions_list(predictions.tail(5))

    return format_predictions_list(today_preds)


def cmd_weekend() -> str:
    predictor = _get_predictor()
    if not predictor.is_ready():
        return "⚠️ მოდელი არ არის ჩატვირთული."

    predictions = predictor.get_latest_predictions(n=100)
    if predictions.empty:
        return "📊 პროგნოზები ვერ მოიძებნა"

    weekend_dates = get_weekend_dates()
    weekend_preds = predictions[predictions["Date"].isin(weekend_dates)]

    if weekend_preds.empty:
        return "📊 შაბათ-კვირის მატჩები ვერ მოიძებნა. ბოლო პროგნოზები:\n\n" + \
               format_predictions_list(predictions.tail(5))

    return format_predictions_list(weekend_preds)


def cmd_predict(team_name: str) -> str:
    if not team_name.strip():
        return "❓ მიუთითეთ გუნდის სახელი: /predict Arsenal"

    predictor = _get_predictor()
    if not predictor.is_ready():
        return "⚠️ მოდელი არ არის ჩატვირთული."

    predictions = predictor.get_latest_predictions(n=100)
    if predictions.empty:
        return "📊 პროგნოზები ვერ მოიძებნა"

    # გუნდის ძიება
    team_lower = team_name.strip().lower()
    mask = (
        predictions["HomeTeam"].str.lower().str.contains(team_lower, na=False) |
        predictions["AwayTeam"].str.lower().str.contains(team_lower, na=False)
    )
    team_preds = predictions[mask]

    if team_preds.empty:
        return f"❓ გუნდი '{team_name}' ვერ მოიძებნა"

    # ბოლო მატჩი
    last = team_preds.iloc[-1]
    pred_dict = {
        "home_team": last["HomeTeam"],
        "away_team": last["AwayTeam"],
        "date": str(last["Date"]),
        "division": last.get("Div", ""),
        "prob_home": float(last.get("prob_H", 0)),
        "prob_draw": float(last.get("prob_D", 0)),
        "prob_away": float(last.get("prob_A", 0)),
        "predicted_result": last.get("predicted", ""),
        "confidence": float(last.get("confidence", 0)),
        "odds_home": float(last.get("B365H", 0)),
        "odds_draw": float(last.get("B365D", 0)),
        "odds_away": float(last.get("B365A", 0)),
    }
    return format_prediction(pred_dict)


def cmd_valuebets() -> str:
    predictor = _get_predictor()
    if not predictor.is_ready():
        return "⚠️ მოდელი არ არის ჩატვირთული."

    predictions = predictor.get_latest_predictions(n=50)
    vb = find_value_bets(predictions)
    return format_value_bets(vb)


def cmd_league(league_code: str) -> str:
    code = league_code.strip().upper()
    if code not in LEAGUES:
        available = "\n".join([f"`{k}` - {v}" for k, v in LEAGUES.items()])
        return f"❓ უცნობი ლიგის კოდი: {code}\n\nხელმისაწვდომი:\n{available}"

    matches = get_all_matches(division=code)
    if matches.empty:
        return f"მატჩები ვერ მოიძებნა: {LEAGUES[code]}"

    standings = _compute_standings(matches)
    return f"🏆 *{LEAGUES[code]}*\n\n" + format_standings(standings)


def cmd_h2h(text: str) -> str:
    if "vs" not in text.lower():
        return "❓ ფორმატი: /h2h Arsenal vs Chelsea"

    parts = text.lower().split("vs")
    if len(parts) != 2:
        return "❓ ფორმატი: /h2h Arsenal vs Chelsea"

    team1 = parts[0].strip()
    team2 = parts[1].strip()

    matches = get_all_matches()
    if matches.empty:
        return "მატჩები ვერ მოიძებნა"

    h2h = matches[
        (matches["home_team"].str.lower().str.contains(team1, na=False) &
         matches["away_team"].str.lower().str.contains(team2, na=False)) |
        (matches["home_team"].str.lower().str.contains(team2, na=False) &
         matches["away_team"].str.lower().str.contains(team1, na=False))
    ]

    return format_h2h(h2h, team1.title(), team2.title())


def cmd_roi() -> str:
    bets = get_bets()
    return format_roi_summary(bets)


def cmd_leagues() -> str:
    lines = ["🏆 *ხელმისაწვდომი ლიგები*\n"]
    for code, name in LEAGUES.items():
        lines.append(f"`{code}` - {name}")
    return "\n".join(lines)


def _compute_standings(df: pd.DataFrame) -> pd.DataFrame:
    teams = set(df["home_team"].unique()) | set(df["away_team"].unique())
    table = []

    for team in teams:
        home = df[df["home_team"] == team]
        away = df[df["away_team"] == team]

        hw = len(home[home["ftr"] == "H"])
        hd = len(home[home["ftr"] == "D"])
        hl = len(home[home["ftr"] == "A"])
        aw = len(away[away["ftr"] == "A"])
        ad = len(away[away["ftr"] == "D"])
        al = len(away[away["ftr"] == "H"])

        played = len(home) + len(away)
        wins = hw + aw
        draws = hd + ad
        losses = hl + al
        gf = int((home["fthg"].sum() or 0) + (away["ftag"].sum() or 0))
        ga = int((home["ftag"].sum() or 0) + (away["fthg"].sum() or 0))
        points = wins * 3 + draws

        table.append({
            "Team": team, "P": played, "W": wins, "D": draws,
            "L": losses, "GF": gf, "GA": ga, "GD": gf - ga, "Pts": points,
        })

    table_df = pd.DataFrame(table)
    table_df = table_df.sort_values(["Pts", "GD", "GF"], ascending=[False, False, False])
    table_df = table_df.reset_index(drop=True)
    table_df.index += 1
    return table_df
