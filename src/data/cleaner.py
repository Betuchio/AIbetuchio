import pandas as pd
import numpy as np
from src.config import REQUIRED_COLUMNS, COLUMN_TYPES
from src.utils.helpers import parse_date
from src.utils.logger import get_logger

log = get_logger(__name__)

# გუნდების სახელების სტანდარტიზაცია
TEAM_NAME_MAP = {
    "Man United": "Manchester United",
    "Man City": "Manchester City",
    "Nott'm Forest": "Nottingham Forest",
    "Nottingham": "Nottingham Forest",
    "Sheffield Utd": "Sheffield United",
    "Sheffield United": "Sheffield United",
    "Wolves": "Wolverhampton",
    "West Ham": "West Ham United",
    "Newcastle": "Newcastle United",
    "Spurs": "Tottenham",
    "Tottenham": "Tottenham Hotspur",
    "Leeds": "Leeds United",
    "Leicester": "Leicester City",
    "Ath Madrid": "Atletico Madrid",
    "Ath Bilbao": "Athletic Bilbao",
    "Betis": "Real Betis",
    "Sociedad": "Real Sociedad",
    "Espanol": "Espanyol",
    "La Coruna": "Deportivo La Coruna",
    "Inter": "Inter Milan",
    "Verona": "Hellas Verona",
    "Parma": "Parma Calcio",
    "Dortmund": "Borussia Dortmund",
    "Leverkusen": "Bayer Leverkusen",
    "M'gladbach": "Borussia Monchengladbach",
    "Ein Frankfurt": "Eintracht Frankfurt",
    "Bayern Munich": "Bayern Munich",
    "St Etienne": "Saint-Etienne",
    "Paris SG": "Paris Saint-Germain",
    "PSG": "Paris Saint-Germain",
}


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """მთავარი გაწმენდის პროცესი."""
    if df.empty:
        return df

    log.info(f"გაწმენდა იწყება: {len(df)} ჩანაწერი")

    # ცარიელი სტრიქონების წაშლა (სადაც ძირითადი სვეტები ცარიელია)
    essential = ["HomeTeam", "AwayTeam", "FTR"]
    for col in essential:
        if col in df.columns:
            df = df.dropna(subset=[col])

    # თარიღის სტანდარტიზაცია
    if "Date" in df.columns:
        df["Date"] = df["Date"].apply(lambda x: parse_date(x))
        df = df.dropna(subset=["Date"])
        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")

    # გუნდების სახელების სტანდარტიზაცია
    for col in ["HomeTeam", "AwayTeam"]:
        if col in df.columns:
            df[col] = df[col].apply(standardize_team_name)

    # რიცხვითი სვეტების კონვერტაცია
    for col, dtype in COLUMN_TYPES.items():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # კოეფიციენტებით: თუ B365 არ არის, სხვა ბუკმეკერის კოეფიციენტები
    df = fill_missing_odds(df)

    # ცარიელი გოლების შევსება NaN-ით (არ წავშალოთ სტრიქონი)
    for col in ["FTHG", "FTAG"]:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)

    log.info(f"გაწმენდის შემდეგ: {len(df)} ჩანაწერი")
    return df


def standardize_team_name(name: str) -> str:
    """გუნდის სახელის სტანდარტიზაცია."""
    if pd.isna(name):
        return name
    name = str(name).strip()
    return TEAM_NAME_MAP.get(name, name)


def fill_missing_odds(df: pd.DataFrame) -> pd.DataFrame:
    """ბუკმეკერების კოეფიციენტების შევსება."""
    # ალტერნატიული ბუკმეკერების სვეტები
    odds_alternatives = {
        "B365H": ["BWH", "IWH", "PSH", "WHH"],
        "B365D": ["BWD", "IWD", "PSD", "WHD"],
        "B365A": ["BWA", "IWA", "PSA", "WHA"],
    }

    for primary, alternatives in odds_alternatives.items():
        if primary in df.columns:
            for alt in alternatives:
                if alt in df.columns:
                    df[primary] = df[primary].fillna(df[alt])

    # თუ ჯერ კიდევ ცარიელია - საშუალო კოეფიციენტებით შევსება
    default_odds = {"B365H": 2.5, "B365D": 3.3, "B365A": 3.5}
    for col, default in default_odds.items():
        if col in df.columns:
            df[col] = df[col].fillna(default)

    return df


def prepare_for_db(df: pd.DataFrame) -> pd.DataFrame:
    """DataFrame-ის მომზადება ბაზაში ჩასმისთვის."""
    # მხოლოდ საჭირო სვეტები
    available_cols = [c for c in REQUIRED_COLUMNS if c in df.columns]
    result = df[available_cols + (["Season"] if "Season" in df.columns else [])].copy()

    # NaN-ების None-ით ჩანაცვლება SQLite-სთვის
    result = result.where(pd.notnull(result), None)

    return result
