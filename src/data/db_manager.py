import sqlite3
import pandas as pd
from src.config import DB_PATH, DB_DIR
from src.utils.logger import get_logger

log = get_logger(__name__)


def get_connection():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_database():
    """ბაზის ცხრილების შექმნა."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            division TEXT,
            season TEXT,
            date TEXT,
            home_team TEXT,
            away_team TEXT,
            fthg INTEGER,
            ftag INTEGER,
            ftr TEXT,
            hthg INTEGER,
            htag INTEGER,
            htr TEXT,
            home_shots INTEGER,
            away_shots INTEGER,
            home_shots_target INTEGER,
            away_shots_target INTEGER,
            home_corners INTEGER,
            away_corners INTEGER,
            odds_home REAL,
            odds_draw REAL,
            odds_away REAL,
            UNIQUE(division, date, home_team, away_team)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER,
            date TEXT,
            home_team TEXT,
            away_team TEXT,
            division TEXT,
            prob_home REAL,
            prob_draw REAL,
            prob_away REAL,
            predicted_result TEXT,
            confidence REAL,
            actual_result TEXT,
            is_correct INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (match_id) REFERENCES matches(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id INTEGER,
            date TEXT,
            home_team TEXT,
            away_team TEXT,
            bet_type TEXT,
            odds REAL,
            stake REAL,
            result TEXT,
            profit REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (prediction_id) REFERENCES predictions(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            model_type TEXT,
            accuracy REAL,
            log_loss REAL,
            train_size INTEGER,
            test_size INTEGER,
            features_used TEXT,
            parameters TEXT,
            notes TEXT
        )
    """)

    conn.commit()
    conn.close()
    log.info("ბაზა ინიციალიზებულია")


def insert_matches(df: pd.DataFrame):
    """მატჩების ჩასმა ბაზაში (დუბლიკატების იგნორი)."""
    conn = get_connection()
    inserted = 0
    for _, row in df.iterrows():
        try:
            conn.execute("""
                INSERT OR IGNORE INTO matches
                (division, season, date, home_team, away_team,
                 fthg, ftag, ftr, hthg, htag, htr,
                 home_shots, away_shots, home_shots_target, away_shots_target,
                 home_corners, away_corners, odds_home, odds_draw, odds_away)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row.get("Div"), row.get("Season"), row.get("Date"),
                row.get("HomeTeam"), row.get("AwayTeam"),
                row.get("FTHG"), row.get("FTAG"), row.get("FTR"),
                row.get("HTHG"), row.get("HTAG"), row.get("HTR"),
                row.get("HS"), row.get("AS"),
                row.get("HST"), row.get("AST"),
                row.get("HC"), row.get("AC"),
                row.get("B365H"), row.get("B365D"), row.get("B365A"),
            ))
            inserted += 1
        except Exception as e:
            log.debug(f"ჩასმის შეცდომა: {e}")
    conn.commit()
    conn.close()
    log.info(f"ჩასმულია {inserted} მატჩი")
    return inserted


def get_all_matches(division: str = None, season: str = None) -> pd.DataFrame:
    """მატჩების წამოღება ბაზიდან."""
    conn = get_connection()
    query = "SELECT * FROM matches WHERE 1=1"
    params = []
    if division:
        query += " AND division = ?"
        params.append(division)
    if season:
        query += " AND season = ?"
        params.append(season)
    query += " ORDER BY date"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_matches_for_prediction(division: str = None) -> pd.DataFrame:
    """მატჩების წამოღება პროგნოზისთვის (ყველა სვეტით)."""
    conn = get_connection()
    query = "SELECT * FROM matches WHERE ftr IS NOT NULL"
    params = []
    if division:
        query += " AND division = ?"
        params.append(division)
    query += " ORDER BY date"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def insert_prediction(prediction: dict):
    """პროგნოზის შენახვა."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO predictions
        (match_id, date, home_team, away_team, division,
         prob_home, prob_draw, prob_away, predicted_result, confidence,
         actual_result, is_correct)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        prediction.get("match_id"),
        prediction.get("date"),
        prediction.get("home_team"),
        prediction.get("away_team"),
        prediction.get("division"),
        prediction.get("prob_home"),
        prediction.get("prob_draw"),
        prediction.get("prob_away"),
        prediction.get("predicted_result"),
        prediction.get("confidence"),
        prediction.get("actual_result"),
        prediction.get("is_correct"),
    ))
    conn.commit()
    conn.close()


def get_predictions(division: str = None, date: str = None) -> pd.DataFrame:
    conn = get_connection()
    query = "SELECT * FROM predictions WHERE 1=1"
    params = []
    if division:
        query += " AND division = ?"
        params.append(division)
    if date:
        query += " AND date = ?"
        params.append(date)
    query += " ORDER BY date DESC, confidence DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def insert_bet(bet: dict):
    """ფსონის შენახვა."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO bets
        (prediction_id, date, home_team, away_team, bet_type, odds, stake, result, profit)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        bet.get("prediction_id"),
        bet.get("date"),
        bet.get("home_team"),
        bet.get("away_team"),
        bet.get("bet_type"),
        bet.get("odds"),
        bet.get("stake"),
        bet.get("result"),
        bet.get("profit"),
    ))
    conn.commit()
    conn.close()


def get_bets() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM bets ORDER BY date DESC", conn)
    conn.close()
    return df


def insert_model_run(run: dict):
    """მოდელის გაწვრთნის ჩანაწერი."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO model_runs
        (model_type, accuracy, log_loss, train_size, test_size,
         features_used, parameters, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run.get("model_type"),
        run.get("accuracy"),
        run.get("log_loss"),
        run.get("train_size"),
        run.get("test_size"),
        run.get("features_used"),
        run.get("parameters"),
        run.get("notes"),
    ))
    conn.commit()
    conn.close()


def get_model_runs() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM model_runs ORDER BY run_date DESC", conn)
    conn.close()
    return df


def update_prediction_result(prediction_id: int, actual_result: str):
    """პროგნოზის შედეგის განახლება."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT predicted_result FROM predictions WHERE id = ?", (prediction_id,))
    row = cursor.fetchone()
    if row:
        is_correct = 1 if row[0] == actual_result else 0
        conn.execute("""
            UPDATE predictions SET actual_result = ?, is_correct = ? WHERE id = ?
        """, (actual_result, is_correct, prediction_id))
    conn.commit()
    conn.close()


def update_bet_result(bet_id: int, result: str):
    """ფსონის შედეგის განახლება."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT odds, stake FROM bets WHERE id = ?", (bet_id,))
    row = cursor.fetchone()
    if row:
        odds, stake = row
        profit = (odds * stake - stake) if result == "won" else -stake
        conn.execute("""
            UPDATE bets SET result = ?, profit = ? WHERE id = ?
        """, (result, profit, bet_id))
    conn.commit()
    conn.close()
