import os
import requests
import pandas as pd
from src.config import (
    FOOTBALL_DATA_BASE_URL, LEAGUES, SEASONS, RAW_DIR
)
from src.utils.logger import get_logger

log = get_logger(__name__)


def download_csv(league: str, season: str) -> str | None:
    """ერთი CSV ფაილის ჩამოტვირთვა football-data.co.uk-დან."""
    url = FOOTBALL_DATA_BASE_URL.format(season=season, league=league)
    filename = f"{league}_{season}.csv"
    filepath = RAW_DIR / filename

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    try:
        log.info(f"ჩამოტვირთვა: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        with open(filepath, "wb") as f:
            f.write(response.content)

        log.info(f"შენახულია: {filepath}")
        return str(filepath)
    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            log.warning(f"ვერ მოიძებნა: {url}")
        else:
            log.error(f"HTTP შეცდომა {url}: {e}")
        return None
    except Exception as e:
        log.error(f"ჩამოტვირთვის შეცდომა {url}: {e}")
        return None


def download_all(leagues: list = None, seasons: list = None) -> list:
    """ყველა ლიგის/სეზონის CSV-ების ჩამოტვირთვა."""
    if leagues is None:
        leagues = list(LEAGUES.keys())
    if seasons is None:
        seasons = SEASONS

    downloaded = []
    total = len(leagues) * len(seasons)
    current = 0

    for league in leagues:
        for season in seasons:
            current += 1
            log.info(f"[{current}/{total}] {LEAGUES.get(league, league)} - {season}")
            filepath = download_csv(league, season)
            if filepath:
                downloaded.append(filepath)

    log.info(f"ჩამოტვირთულია {len(downloaded)}/{total} ფაილი")
    return downloaded


def load_csv(filepath: str) -> pd.DataFrame | None:
    """CSV ფაილის წაკითხვა DataFrame-ში."""
    try:
        df = pd.read_csv(filepath, encoding="utf-8", on_bad_lines="skip")
        if df.empty:
            log.warning(f"ცარიელი ფაილი: {filepath}")
            return None
        return df
    except Exception as e:
        log.error(f"CSV წაკითხვის შეცდომა {filepath}: {e}")
        try:
            df = pd.read_csv(filepath, encoding="latin-1", on_bad_lines="skip")
            return df
        except Exception as e2:
            log.error(f"მეორე მცდელობაც ვერ მოხერხდა: {e2}")
            return None


def load_all_raw_data() -> pd.DataFrame:
    """ყველა raw CSV-ის ერთ DataFrame-ში გაერთიანება."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    all_dfs = []

    csv_files = sorted(RAW_DIR.glob("*.csv"))
    if not csv_files:
        log.warning("არცერთი CSV ფაილი არ მოიძებნა raw/ ფოლდერში")
        return pd.DataFrame()

    for csv_file in csv_files:
        df = load_csv(str(csv_file))
        if df is not None and not df.empty:
            # ფაილის სახელიდან სეზონის ამოღება
            parts = csv_file.stem.split("_")
            if len(parts) == 2:
                df["Season"] = parts[1]
            all_dfs.append(df)

    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        log.info(f"გაერთიანებულია {len(all_dfs)} ფაილი, სულ {len(combined)} მატჩი")
        return combined

    return pd.DataFrame()
