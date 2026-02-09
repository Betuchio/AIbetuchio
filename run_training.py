"""მოდელის გაწვრთნა."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ml.trainer import MatchPredictor
from src.data.db_manager import init_database
from src.utils.logger import get_logger

log = get_logger(__name__)


def main():
    log.info("=" * 60)
    log.info("AIbetuchio - მოდელის გაწვრთნა")
    log.info("=" * 60)

    init_database()

    trainer = MatchPredictor()
    results = trainer.train()

    if results:
        log.info("\n" + "=" * 40)
        log.info("შედეგები:")
        log.info(f"  მოდელი: {results['model_type']}")
        log.info(f"  Accuracy: {results['accuracy']:.4f} ({results['accuracy']*100:.1f}%)")
        log.info(f"  Log Loss: {results['log_loss']:.4f}")
        log.info(f"  XGBoost Accuracy: {results['xgb_accuracy']:.4f}")
        log.info(f"  LR Accuracy: {results['lr_accuracy']:.4f}")
        log.info(f"  Train/Test: {results['train_size']}/{results['test_size']}")

        if results.get("feature_importance"):
            log.info("\nTop 10 ფიჩერი:")
            for i, (feat, imp) in enumerate(
                list(results["feature_importance"].items())[:10], 1
            ):
                log.info(f"  {i}. {feat}: {imp:.4f}")

        log.info("=" * 40)
    else:
        log.error("გაწვრთნა ვერ მოხერხდა. შეამოწმეთ მონაცემები (setup_data.py)")


if __name__ == "__main__":
    main()
