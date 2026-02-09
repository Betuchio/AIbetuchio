"""ML მოდელის გაწვრთნა."""
import json
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, log_loss, confusion_matrix, classification_report
from xgboost import XGBClassifier
import joblib

from src.config import MODEL_PATH, MODEL_METADATA_PATH, MODELS_DIR
from src.data.db_manager import get_all_matches, insert_model_run
from src.data.feature_engineer import create_features, get_feature_columns
from src.utils.logger import get_logger

log = get_logger(__name__)


class MatchPredictor:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_columns = []
        self.metadata = {}

    def prepare_data(self, df: pd.DataFrame) -> tuple:
        """მონაცემების მომზადება ML-ისთვის."""
        log.info("მონაცემების მომზადება...")

        # ფიჩერების შექმნა
        featured_df = create_features(df)

        if featured_df.empty:
            log.error("ფიჩერების შექმნა ვერ მოხერხდა")
            return None, None, None

        # ფიჩერების სვეტები
        self.feature_columns = get_feature_columns(featured_df)
        log.info(f"ფიჩერების რაოდენობა: {len(self.feature_columns)}")

        # X და y
        X = featured_df[self.feature_columns].copy()
        y = featured_df["FTR"].copy()

        # NaN-ების შევსება მედიანით
        X = X.fillna(X.median())

        # ლეიბელ ენკოდინგი: H=0, D=1, A=2
        self.label_encoder.fit(["A", "D", "H"])
        y_encoded = self.label_encoder.transform(y)

        return X, y_encoded, featured_df

    def train(self, test_ratio: float = 0.2) -> dict:
        """მოდელის გაწვრთნა."""
        log.info("=" * 50)
        log.info("მოდელის გაწვრთნა იწყება")
        log.info("=" * 50)

        # მონაცემების ჩატვირთვა
        df = get_all_matches()
        if df.empty:
            log.error("ბაზაში მატჩები არ მოიძებნა")
            return {}

        log.info(f"სულ მატჩები ბაზაში: {len(df)}")

        X, y, featured_df = self.prepare_data(df)
        if X is None:
            return {}

        # დროზე დაფუძნებული გაყოფა (არა random!)
        split_idx = int(len(X) * (1 - test_ratio))
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        log.info(f"Train: {len(X_train)}, Test: {len(X_test)}")

        # სკალირება
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # === XGBoost ===
        log.info("XGBoost-ის გაწვრთნა...")
        xgb_params = {
            "n_estimators": [100, 200],
            "max_depth": [3, 5, 7],
            "learning_rate": [0.05, 0.1],
            "subsample": [0.8],
            "colsample_bytree": [0.8],
        }

        xgb = XGBClassifier(
            objective="multi:softprob",
            num_class=3,
            eval_metric="mlogloss",
            random_state=42,
        )

        tscv = TimeSeriesSplit(n_splits=3)
        grid_search = GridSearchCV(
            xgb, xgb_params,
            cv=tscv,
            scoring="accuracy",
            n_jobs=-1,
            verbose=0,
        )
        grid_search.fit(X_train_scaled, y_train)

        best_xgb = grid_search.best_estimator_
        xgb_pred = best_xgb.predict(X_test_scaled)
        xgb_proba = best_xgb.predict_proba(X_test_scaled)

        xgb_accuracy = accuracy_score(y_test, xgb_pred)
        xgb_logloss = log_loss(y_test, xgb_proba)

        log.info(f"XGBoost - Accuracy: {xgb_accuracy:.4f}, Log Loss: {xgb_logloss:.4f}")
        log.info(f"საუკეთესო პარამეტრები: {grid_search.best_params_}")

        # === Logistic Regression (baseline) ===
        log.info("Logistic Regression (baseline)...")
        lr = LogisticRegression(max_iter=1000, random_state=42)
        lr.fit(X_train_scaled, y_train)
        lr_pred = lr.predict(X_test_scaled)
        lr_proba = lr.predict_proba(X_test_scaled)

        lr_accuracy = accuracy_score(y_test, lr_pred)
        lr_logloss = log_loss(y_test, lr_proba)

        log.info(f"Logistic Regression - Accuracy: {lr_accuracy:.4f}, Log Loss: {lr_logloss:.4f}")

        # საუკეთესო მოდელის არჩევა
        if xgb_accuracy >= lr_accuracy:
            self.model = best_xgb
            best_accuracy = xgb_accuracy
            best_logloss = xgb_logloss
            model_type = "XGBoost"
            best_pred = xgb_pred
            log.info("არჩეულია: XGBoost")
        else:
            self.model = lr
            best_accuracy = lr_accuracy
            best_logloss = lr_logloss
            model_type = "LogisticRegression"
            best_pred = lr_pred
            log.info("არჩეულია: Logistic Regression")

        # Confusion Matrix
        cm = confusion_matrix(y_test, best_pred)
        report = classification_report(
            y_test, best_pred,
            target_names=self.label_encoder.classes_,
            output_dict=True
        )

        log.info(f"\nConfusion Matrix:\n{cm}")
        log.info(f"\nClassification Report:\n{classification_report(y_test, best_pred, target_names=self.label_encoder.classes_)}")

        # Feature Importance
        feature_importance = {}
        if hasattr(self.model, "feature_importances_"):
            importances = self.model.feature_importances_
            for feat, imp in sorted(
                zip(self.feature_columns, importances),
                key=lambda x: x[1], reverse=True
            ):
                feature_importance[feat] = float(imp)

        # მოდელის შენახვა
        self._save_model(model_type, best_accuracy, best_logloss,
                         len(X_train), len(X_test), feature_importance,
                         grid_search.best_params_ if model_type == "XGBoost" else {},
                         cm.tolist(), report)

        # DB-ში ჩაწერა
        insert_model_run({
            "model_type": model_type,
            "accuracy": best_accuracy,
            "log_loss": best_logloss,
            "train_size": len(X_train),
            "test_size": len(X_test),
            "features_used": json.dumps(self.feature_columns),
            "parameters": json.dumps(grid_search.best_params_ if model_type == "XGBoost" else {}),
            "notes": f"XGB: {xgb_accuracy:.4f}, LR: {lr_accuracy:.4f}",
        })

        results = {
            "model_type": model_type,
            "accuracy": best_accuracy,
            "log_loss": best_logloss,
            "xgb_accuracy": xgb_accuracy,
            "lr_accuracy": lr_accuracy,
            "train_size": len(X_train),
            "test_size": len(X_test),
            "confusion_matrix": cm.tolist(),
            "classification_report": report,
            "feature_importance": feature_importance,
            "best_params": grid_search.best_params_,
        }

        log.info("მოდელის გაწვრთნა დასრულდა!")
        return results

    def _save_model(self, model_type, accuracy, logloss,
                    train_size, test_size, feature_importance,
                    params, cm, report):
        """მოდელის და მეტადატის შენახვა."""
        MODELS_DIR.mkdir(parents=True, exist_ok=True)

        # მოდელის შენახვა
        model_data = {
            "model": self.model,
            "scaler": self.scaler,
            "label_encoder": self.label_encoder,
            "feature_columns": self.feature_columns,
        }
        joblib.dump(model_data, str(MODEL_PATH))
        log.info(f"მოდელი შენახულია: {MODEL_PATH}")

        # მეტადატა
        self.metadata = {
            "model_type": model_type,
            "trained_at": datetime.now().isoformat(),
            "accuracy": accuracy,
            "log_loss": logloss,
            "train_size": train_size,
            "test_size": test_size,
            "feature_count": len(self.feature_columns),
            "feature_columns": self.feature_columns,
            "feature_importance": feature_importance,
            "parameters": params,
            "confusion_matrix": cm,
            "classification_report": report,
        }

        with open(str(MODEL_METADATA_PATH), "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        log.info(f"მეტადატა შენახულია: {MODEL_METADATA_PATH}")
