import os
from pathlib import Path

# === პროექტის ძირითადი პათები ===
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
UPLOADS_DIR = DATA_DIR / "uploads"
MODELS_DIR = BASE_DIR / "models"
DB_DIR = BASE_DIR / "database"
DB_PATH = DB_DIR / "aibetuchio.db"

# === ლიგების კონფიგურაცია ===
LEAGUES = {
    "E0": "Premier League",
    "SP1": "La Liga",
    "I1": "Serie A",
    "D1": "Bundesliga",
    "F1": "Ligue 1",
    "N1": "Eredivisie",
    "B1": "Jupiler League",
    "P1": "Liga Portugal",
    "T1": "Super Lig",
    "G1": "Super League Greece",
}

# === სეზონები (football-data.co.uk ფორმატი) ===
SEASONS = ["2122", "2223", "2324", "2425"]
SEASON_LABELS = {
    "2122": "2021/22",
    "2223": "2022/23",
    "2324": "2023/24",
    "2425": "2024/25",
}

# === მონაცემების წყარო ===
FOOTBALL_DATA_BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"

# === ML კონფიგურაცია ===
MODEL_PATH = MODELS_DIR / "match_predictor.joblib"
MODEL_METADATA_PATH = MODELS_DIR / "model_metadata.json"
MIN_EDGE_THRESHOLD = 0.05  # 5% მინიმალური edge value bet-ისთვის
FORM_WINDOW = 5  # ბოლო 5 მატჩის ფორმა
ROLLING_WINDOW = 5  # rolling average ფანჯარა

# === სვეტების კონფიგურაცია ===
# football-data.co.uk CSV სვეტები, რომლებიც გვჭირდება
REQUIRED_COLUMNS = [
    "Div", "Date", "HomeTeam", "AwayTeam",
    "FTHG", "FTAG", "FTR",
    "HTHG", "HTAG", "HTR",
    "HS", "AS", "HST", "AST",
    "HC", "AC",
    "B365H", "B365D", "B365A",
]

# სვეტების ტიპების მაპინგი
COLUMN_TYPES = {
    "FTHG": "float", "FTAG": "float",
    "HTHG": "float", "HTAG": "float",
    "HS": "float", "AS": "float",
    "HST": "float", "AST": "float",
    "HC": "float", "AC": "float",
    "B365H": "float", "B365D": "float", "B365A": "float",
}

# === Telegram ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "your_token_here")

# === ვებ ===
STREAMLIT_PORT = 8501
