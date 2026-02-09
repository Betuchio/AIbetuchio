"""პროგნოზების გაკეთება გაწვრთნილი მოდელით."""
import json
import numpy as np
import pandas as pd
import joblib

from src.config import MODEL_PATH, MODEL_METADATA_PATH
from src.data.db_manager import get_all_matches, insert_prediction
from src.data.feature_engineer import create_features, get_feature_columns
from src.utils.logger import get_logger

log = get_logger(__name__)


class Predictor:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.label_encoder = None
        self.feature_columns = []
        self.metadata = {}
        self._load_model()

    def _load_model(self):
        """გაწვრთნილი მოდელის ჩატვირთვა."""
        try:
            model_data = joblib.load(str(MODEL_PATH))
            self.model = model_data["model"]
            self.scaler = model_data["scaler"]
            self.label_encoder = model_data["label_encoder"]
            self.feature_columns = model_data["feature_columns"]

            with open(str(MODEL_METADATA_PATH), "r", encoding="utf-8") as f:
                self.metadata = json.load(f)

            log.info(f"მოდელი ჩატვირთულია: {self.metadata.get('model_type')}")
        except FileNotFoundError:
            log.warning("გაწვრთნილი მოდელი ვერ მოიძებნა. ჯერ გაუშვით run_training.py")
        except Exception as e:
            log.error(f"მოდელის ჩატვირთვის შეცდომა: {e}")

    def is_ready(self) -> bool:
        return self.model is not None

    def predict_matches(self, division: str = None, upcoming_only: bool = False) -> pd.DataFrame:
        """მატჩების პროგნოზირება."""
        if not self.is_ready():
            log.error("მოდელი არ არის ჩატვირთული")
            return pd.DataFrame()

        df = get_all_matches(division=division)
        if df.empty:
            log.warning("მატჩები ვერ მოიძებნა")
            return pd.DataFrame()

        featured_df = create_features(df)
        if featured_df.empty:
            return pd.DataFrame()

        # ფიჩერების მომზადება
        available_features = [c for c in self.feature_columns if c in featured_df.columns]
        if len(available_features) < len(self.feature_columns) * 0.5:
            log.error("ძალიან ბევრი ფიჩერი აკლია")
            return pd.DataFrame()

        X = featured_df[available_features].copy()
        X = X.fillna(X.median())

        # დაკლებული ფიჩერების დამატება 0-ით
        for col in self.feature_columns:
            if col not in X.columns:
                X[col] = 0
        X = X[self.feature_columns]

        # სკალირება და პროგნოზი
        X_scaled = self.scaler.transform(X)
        probabilities = self.model.predict_proba(X_scaled)
        predictions = self.model.predict(X_scaled)

        # შედეგების DataFrame
        result = featured_df[["Date", "HomeTeam", "AwayTeam", "Div", "FTR",
                               "B365H", "B365D", "B365A"]].copy()
        result = result.iloc[-len(predictions):]

        labels = self.label_encoder.classes_
        for i, label in enumerate(labels):
            result[f"prob_{label}"] = probabilities[:, i]

        result["predicted"] = self.label_encoder.inverse_transform(predictions)

        # confidence = მაქსიმალური ალბათობა
        result["confidence"] = probabilities.max(axis=1)

        # სწორია თუ არა
        result["is_correct"] = (result["predicted"] == result["FTR"]).astype(int)

        return result

    def predict_single(self, home_team: str, away_team: str,
                       division: str = None) -> dict | None:
        """ერთი მატჩის პროგნოზი."""
        predictions = self.predict_matches(division=division)
        if predictions.empty:
            return None

        mask = (
            (predictions["HomeTeam"].str.lower() == home_team.lower()) |
            (predictions["AwayTeam"].str.lower() == away_team.lower())
        )

        if home_team.lower() and away_team.lower():
            mask = (
                (predictions["HomeTeam"].str.lower() == home_team.lower()) &
                (predictions["AwayTeam"].str.lower() == away_team.lower())
            )

        match = predictions[mask]
        if match.empty:
            return None

        row = match.iloc[-1]
        return {
            "date": str(row["Date"]),
            "home_team": row["HomeTeam"],
            "away_team": row["AwayTeam"],
            "division": row["Div"],
            "prob_home": float(row.get("prob_H", 0)),
            "prob_draw": float(row.get("prob_D", 0)),
            "prob_away": float(row.get("prob_A", 0)),
            "predicted_result": row["predicted"],
            "confidence": float(row["confidence"]),
            "odds_home": float(row.get("B365H", 0)),
            "odds_draw": float(row.get("B365D", 0)),
            "odds_away": float(row.get("B365A", 0)),
        }

    def get_latest_predictions(self, n: int = 20, division: str = None) -> pd.DataFrame:
        """ბოლო N პროგნოზი."""
        predictions = self.predict_matches(division=division)
        if predictions.empty:
            return predictions
        return predictions.tail(n)

    def save_predictions_to_db(self, predictions: pd.DataFrame):
        """პროგნოზების ბაზაში შენახვა."""
        for _, row in predictions.iterrows():
            pred = {
                "match_id": None,
                "date": str(row["Date"]),
                "home_team": row["HomeTeam"],
                "away_team": row["AwayTeam"],
                "division": row.get("Div", ""),
                "prob_home": float(row.get("prob_H", 0)),
                "prob_draw": float(row.get("prob_D", 0)),
                "prob_away": float(row.get("prob_A", 0)),
                "predicted_result": row["predicted"],
                "confidence": float(row["confidence"]),
                "actual_result": row.get("FTR"),
                "is_correct": int(row.get("is_correct", 0)),
            }
            insert_prediction(pred)
        log.info(f"{len(predictions)} პროგნოზი შენახულია ბაზაში")
