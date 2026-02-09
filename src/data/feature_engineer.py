import pandas as pd
import numpy as np
from src.config import FORM_WINDOW, ROLLING_WINDOW
from src.utils.helpers import implied_probabilities
from src.utils.logger import get_logger

log = get_logger(__name__)


def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """მატჩის მონაცემებიდან ML ფიჩერების შექმნა.

    მნიშვნელოვანი: ყველა ფიჩერი იყენებს მხოლოდ მატჩამდე
    ხელმისაწვდომ ინფორმაციას (no data leakage).
    """
    if df.empty:
        return df

    log.info("ფიჩერების შექმნა იწყება...")

    df = df.copy()
    df["Date"] = pd.to_datetime(df["date"] if "date" in df.columns else df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)

    # სვეტების სტანდარტიზაცია (DB-ში სხვა სახელებია)
    col_map = {
        "home_team": "HomeTeam", "away_team": "AwayTeam",
        "fthg": "FTHG", "ftag": "FTAG", "ftr": "FTR",
        "home_shots": "HS", "away_shots": "AS",
        "home_shots_target": "HST", "away_shots_target": "AST",
        "home_corners": "HC", "away_corners": "AC",
        "odds_home": "B365H", "odds_draw": "B365D", "odds_away": "B365A",
        "division": "Div",
    }
    for old, new in col_map.items():
        if old in df.columns and new not in df.columns:
            df[new] = df[old]

    # რიცხვითი სვეტების კონვერტაცია
    num_cols = ["FTHG", "FTAG", "HS", "AS", "HST", "AST", "HC", "AC",
                "B365H", "B365D", "B365A"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    all_features = []

    # თითოეული ლიგისთვის ცალკე
    for div in df["Div"].unique():
        div_df = df[df["Div"] == div].copy()
        div_features = _compute_division_features(div_df)
        all_features.append(div_features)

    result = pd.concat(all_features, ignore_index=True)

    # კოეფიციენტებიდან ფიჩერები (ლიგისგან დამოუკიდებელი)
    result = _add_odds_features(result)

    # NaN-ების წაშლა (პირველი რამდენიმე მატჩს არ ექნება ისტორია)
    feature_cols = [c for c in result.columns if c.startswith("feat_")]
    before = len(result)
    result = result.dropna(subset=feature_cols)
    log.info(f"ფიჩერები შექმნილია: {len(result)} მატჩი ({before - len(result)} ამოღებული)")

    return result


def _compute_division_features(df: pd.DataFrame) -> pd.DataFrame:
    """ერთი ლიგის ფიჩერების გამოთვლა."""
    df = df.sort_values("Date").reset_index(drop=True)

    # ყველა გუნდის ისტორიის აგება
    teams = set(df["HomeTeam"].unique()) | set(df["AwayTeam"].unique())
    team_history = {t: [] for t in teams}

    features_list = []

    for idx, row in df.iterrows():
        home = row["HomeTeam"]
        away = row["AwayTeam"]

        home_hist = team_history[home]
        away_hist = team_history[away]

        feats = {}

        # --- გუნდის ფორმა ---
        feats.update(_form_features(home_hist, "home", home))
        feats.update(_form_features(away_hist, "away", away))

        # --- H2H ---
        feats.update(_h2h_features(home_hist + away_hist, home, away))

        # --- ლიგის სიძლიერის ინდექსი ---
        feats.update(_strength_index(df.iloc[:idx], home, away))

        features_list.append(feats)

        # ისტორიის განახლება (მატჩის შემდეგ)
        match_info = {
            "date": row["Date"],
            "home": home, "away": away,
            "fthg": row.get("FTHG", 0), "ftag": row.get("FTAG", 0),
            "ftr": row.get("FTR", ""),
            "hs": row.get("HS"), "as_": row.get("AS"),
            "hst": row.get("HST"), "ast": row.get("AST"),
            "hc": row.get("HC"), "ac": row.get("AC"),
        }
        team_history[home].append(match_info)
        team_history[away].append(match_info)

    feat_df = pd.DataFrame(features_list)
    return pd.concat([df.reset_index(drop=True), feat_df], axis=1)


def _form_features(history: list, prefix: str, team: str) -> dict:
    """გუნდის ფორმის ფიჩერები ბოლო N მატჩიდან."""
    feats = {}
    window = FORM_WINDOW

    if len(history) < 3:
        # არასაკმარისი ისტორია
        feats[f"feat_{prefix}_form_points"] = np.nan
        feats[f"feat_{prefix}_form_goals_scored"] = np.nan
        feats[f"feat_{prefix}_form_goals_conceded"] = np.nan
        feats[f"feat_{prefix}_form_win_rate"] = np.nan
        feats[f"feat_{prefix}_form_shots"] = np.nan
        feats[f"feat_{prefix}_form_shots_target"] = np.nan
        feats[f"feat_{prefix}_form_corners"] = np.nan
        return feats

    recent = history[-window:]
    points = []
    goals_scored = []
    goals_conceded = []
    shots = []
    shots_target = []
    corners = []

    for m in recent:
        is_home = m["home"] == team
        gs = m["fthg"] if is_home else m["ftag"]
        gc = m["ftag"] if is_home else m["fthg"]
        goals_scored.append(gs or 0)
        goals_conceded.append(gc or 0)

        ftr = m["ftr"]
        if (is_home and ftr == "H") or (not is_home and ftr == "A"):
            points.append(3)
        elif ftr == "D":
            points.append(1)
        else:
            points.append(0)

        s = m["hs"] if is_home else m["as_"]
        st = m["hst"] if is_home else m["ast"]
        c = m["hc"] if is_home else m["ac"]
        if s is not None and not (isinstance(s, float) and np.isnan(s)):
            shots.append(s)
        if st is not None and not (isinstance(st, float) and np.isnan(st)):
            shots_target.append(st)
        if c is not None and not (isinstance(c, float) and np.isnan(c)):
            corners.append(c)

    n = len(recent)
    feats[f"feat_{prefix}_form_points"] = sum(points) / n if n else 0
    feats[f"feat_{prefix}_form_goals_scored"] = np.mean(goals_scored) if goals_scored else 0
    feats[f"feat_{prefix}_form_goals_conceded"] = np.mean(goals_conceded) if goals_conceded else 0
    wins = sum(1 for p in points if p == 3)
    feats[f"feat_{prefix}_form_win_rate"] = wins / n if n else 0
    feats[f"feat_{prefix}_form_shots"] = np.mean(shots) if shots else np.nan
    feats[f"feat_{prefix}_form_shots_target"] = np.mean(shots_target) if shots_target else np.nan
    feats[f"feat_{prefix}_form_corners"] = np.mean(corners) if corners else np.nan

    return feats


def _h2h_features(combined_history: list, home: str, away: str) -> dict:
    """პირისპირ შეხვედრების ფიჩერები."""
    feats = {}

    h2h = [m for m in combined_history
           if (m["home"] == home and m["away"] == away) or
              (m["home"] == away and m["away"] == home)]

    h2h = h2h[-5:]  # ბოლო 5

    if len(h2h) < 2:
        feats["feat_h2h_home_wins"] = np.nan
        feats["feat_h2h_draws"] = np.nan
        feats["feat_h2h_away_wins"] = np.nan
        feats["feat_h2h_home_goals_avg"] = np.nan
        return feats

    home_wins = 0
    draws = 0
    away_wins = 0
    home_goals = []

    for m in h2h:
        if m["home"] == home:
            if m["ftr"] == "H":
                home_wins += 1
            elif m["ftr"] == "D":
                draws += 1
            else:
                away_wins += 1
            home_goals.append(m["fthg"] or 0)
        else:
            if m["ftr"] == "A":
                home_wins += 1
            elif m["ftr"] == "D":
                draws += 1
            else:
                away_wins += 1
            home_goals.append(m["ftag"] or 0)

    n = len(h2h)
    feats["feat_h2h_home_wins"] = home_wins / n
    feats["feat_h2h_draws"] = draws / n
    feats["feat_h2h_away_wins"] = away_wins / n
    feats["feat_h2h_home_goals_avg"] = np.mean(home_goals)

    return feats


def _strength_index(past_matches: pd.DataFrame, home: str, away: str) -> dict:
    """შეტევის/დაცვის სიძლიერის ინდექსი."""
    feats = {}

    if len(past_matches) < 20:
        feats["feat_home_attack_strength"] = np.nan
        feats["feat_home_defense_strength"] = np.nan
        feats["feat_away_attack_strength"] = np.nan
        feats["feat_away_defense_strength"] = np.nan
        feats["feat_home_league_position"] = np.nan
        feats["feat_away_league_position"] = np.nan
        return feats

    league_avg_home_goals = past_matches["FTHG"].mean()
    league_avg_away_goals = past_matches["FTAG"].mean()

    if league_avg_home_goals == 0:
        league_avg_home_goals = 1.0
    if league_avg_away_goals == 0:
        league_avg_away_goals = 1.0

    for team, prefix in [(home, "home"), (away, "away")]:
        home_matches = past_matches[past_matches["HomeTeam"] == team]
        away_matches = past_matches[past_matches["AwayTeam"] == team]

        if len(home_matches) >= 3:
            attack_home = home_matches["FTHG"].mean() / league_avg_home_goals
            defense_home = home_matches["FTAG"].mean() / league_avg_away_goals
        else:
            attack_home = 1.0
            defense_home = 1.0

        if len(away_matches) >= 3:
            attack_away = away_matches["FTAG"].mean() / league_avg_away_goals
            defense_away = away_matches["FTHG"].mean() / league_avg_home_goals
        else:
            attack_away = 1.0
            defense_away = 1.0

        feats[f"feat_{prefix}_attack_strength"] = (attack_home + attack_away) / 2
        feats[f"feat_{prefix}_defense_strength"] = (defense_home + defense_away) / 2

    # ლიგის პოზიცია (გამარტივებული - ქულებით)
    standings = _compute_standings(past_matches)
    feats["feat_home_league_position"] = standings.get(home, 10) / max(len(standings), 1)
    feats["feat_away_league_position"] = standings.get(away, 10) / max(len(standings), 1)

    return feats


def _compute_standings(df: pd.DataFrame) -> dict:
    """ლიგის ცხრილის გამოთვლა."""
    points = {}

    for _, row in df.iterrows():
        home = row["HomeTeam"]
        away = row["AwayTeam"]
        ftr = row.get("FTR", "")

        if home not in points:
            points[home] = 0
        if away not in points:
            points[away] = 0

        if ftr == "H":
            points[home] += 3
        elif ftr == "D":
            points[home] += 1
            points[away] += 1
        elif ftr == "A":
            points[away] += 3

    # პოზიციის მინიჭება
    sorted_teams = sorted(points.items(), key=lambda x: x[1], reverse=True)
    positions = {}
    for i, (team, _) in enumerate(sorted_teams, 1):
        positions[team] = i

    return positions


def _add_odds_features(df: pd.DataFrame) -> pd.DataFrame:
    """კოეფიციენტებიდან ფიჩერების დამატება."""
    df = df.copy()

    if all(c in df.columns for c in ["B365H", "B365D", "B365A"]):
        probs = df.apply(
            lambda r: implied_probabilities(r["B365H"], r["B365D"], r["B365A"]),
            axis=1
        )
        df["feat_implied_prob_home"] = probs.apply(lambda x: x[0])
        df["feat_implied_prob_draw"] = probs.apply(lambda x: x[1])
        df["feat_implied_prob_away"] = probs.apply(lambda x: x[2])

        # კოეფიციენტებიდან ფავორიტის ინდიკატორი
        df["feat_odds_favorite"] = df[["B365H", "B365D", "B365A"]].idxmin(axis=1)
        df["feat_odds_favorite"] = df["feat_odds_favorite"].map({
            "B365H": 0, "B365D": 1, "B365A": 2
        })

    return df


def get_feature_columns(df: pd.DataFrame) -> list:
    """ფიჩერ სვეტების სია."""
    return [c for c in df.columns if c.startswith("feat_")]
