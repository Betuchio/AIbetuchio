"""პირველადი მონაცემების ჩამოტვირთვა და ბაზაში ჩატვირთვა."""
import sys
import os

# პროექტის root-ის დამატება path-ში
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data.collector import download_all, load_all_raw_data
from src.data.cleaner import clean_dataframe, prepare_for_db
from src.data.db_manager import init_database, insert_matches
from src.utils.logger import get_logger

log = get_logger(__name__)


def main():
    log.info("=" * 60)
    log.info("AIbetuchio - მონაცემების ინიციალიზაცია")
    log.info("=" * 60)

    # 1. ბაზის შექმნა
    log.info("ნაბიჯი 1: ბაზის ინიციალიზაცია...")
    init_database()

    # 2. CSV-ების ჩამოტვირთვა
    log.info("ნაბიჯი 2: CSV ფაილების ჩამოტვირთვა...")
    downloaded = download_all()
    log.info(f"ჩამოტვირთულია {len(downloaded)} ფაილი")

    # 3. მონაცემების გაერთიანება
    log.info("ნაბიჯი 3: მონაცემების გაერთიანება...")
    raw_df = load_all_raw_data()
    if raw_df.empty:
        log.error("მონაცემები ვერ ჩაიტვირთა!")
        return

    log.info(f"სულ ჩანაწერები: {len(raw_df)}")

    # 4. გაწმენდა
    log.info("ნაბიჯი 4: მონაცემების გაწმენდა...")
    clean_df = clean_dataframe(raw_df)
    log.info(f"გაწმენდილი ჩანაწერები: {len(clean_df)}")

    # 5. ბაზაში ჩატვირთვა
    log.info("ნაბიჯი 5: ბაზაში ჩატვირთვა...")
    db_df = prepare_for_db(clean_df)
    inserted = insert_matches(db_df)
    log.info(f"ბაზაში ჩასმულია: {inserted} მატჩი")

    log.info("=" * 60)
    log.info("მონაცემების ინიციალიზაცია დასრულდა!")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
