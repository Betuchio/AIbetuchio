"""მონაცემები - მონაცემების ჩამოტვირთვა და მართვა."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import streamlit as st
import pandas as pd

from src.data.collector import download_all, download_csv, load_csv
from src.data.cleaner import clean_dataframe, prepare_for_db
from src.data.db_manager import init_database, insert_matches, get_all_matches
from src.config import LEAGUES, SEASONS, SEASON_LABELS, UPLOADS_DIR

st.set_page_config(page_title="მონაცემები - AIbetuchio", page_icon="📂", layout="wide")
st.title("📂 მონაცემების მართვა")

# ბაზის სტატუსი
st.subheader("ბაზის მდგომარეობა")
matches = get_all_matches()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("სულ მატჩები", len(matches))
with col2:
    if not matches.empty and "division" in matches.columns:
        st.metric("ლიგები", matches["division"].nunique())
    else:
        st.metric("ლიგები", 0)
with col3:
    if not matches.empty and "season" in matches.columns:
        st.metric("სეზონები", matches["season"].nunique())
    else:
        st.metric("სეზონები", 0)

if not matches.empty and "division" in matches.columns:
    league_counts = matches.groupby("division").size().reset_index(name="მატჩები")
    league_counts["ლიგა"] = league_counts["division"].map(LEAGUES)
    league_counts = league_counts[["ლიგა", "division", "მატჩები"]].rename(columns={"division": "კოდი"})
    st.dataframe(league_counts, use_container_width=True)

# მონაცემების ჩამოტვირთვა
st.markdown("---")
st.subheader("მონაცემების ჩამოტვირთვა")

col1, col2 = st.columns(2)
with col1:
    selected_leagues = st.multiselect(
        "ლიგები",
        options=list(LEAGUES.keys()),
        default=list(LEAGUES.keys()),
        format_func=lambda x: f"{LEAGUES[x]} ({x})",
    )
with col2:
    selected_seasons = st.multiselect(
        "სეზონები",
        options=SEASONS,
        default=SEASONS,
        format_func=lambda x: SEASON_LABELS.get(x, x),
    )

if st.button("ჩამოტვირთვა და განახლება", type="primary"):
    with st.spinner("მიმდინარეობს ჩამოტვირთვა..."):
        init_database()
        downloaded = download_all(leagues=selected_leagues, seasons=selected_seasons)
        st.write(f"ჩამოტვირთულია: {len(downloaded)} ფაილი")

        if downloaded:
            from src.data.collector import load_all_raw_data
            raw_df = load_all_raw_data()
            if not raw_df.empty:
                clean_df = clean_dataframe(raw_df)
                db_df = prepare_for_db(clean_df)
                inserted = insert_matches(db_df)
                st.success(f"ბაზაში ჩასმულია: {inserted} ახალი მატჩი")
            else:
                st.warning("მონაცემები ცარიელია")

# CSV ატვირთვა
st.markdown("---")
st.subheader("CSV ფაილის ატვირთვა")

uploaded_file = st.file_uploader("აირჩიეთ CSV ფაილი", type=["csv"])

if uploaded_file is not None:
    try:
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        df = pd.read_csv(uploaded_file)
        st.write(f"ჩანაწერები: {len(df)}")
        st.write("სვეტები:", list(df.columns))
        st.dataframe(df.head(10), use_container_width=True)

        if st.button("ბაზაში ჩატვირთვა"):
            with st.spinner("მიმდინარეობს..."):
                init_database()
                clean_df = clean_dataframe(df)
                db_df = prepare_for_db(clean_df)
                inserted = insert_matches(db_df)
                st.success(f"ჩასმულია: {inserted} მატჩი")
    except Exception as e:
        st.error(f"შეცდომა: {e}")

# ცალკეული ფაილი
st.markdown("---")
st.subheader("ცალკეული ლიგის/სეზონის ჩამოტვირთვა")

col1, col2 = st.columns(2)
with col1:
    single_league = st.selectbox(
        "ლიგა",
        options=list(LEAGUES.keys()),
        format_func=lambda x: f"{LEAGUES[x]} ({x})",
        key="single_league",
    )
with col2:
    single_season = st.selectbox(
        "სეზონი",
        options=SEASONS,
        format_func=lambda x: SEASON_LABELS.get(x, x),
        key="single_season",
    )

if st.button("ჩამოტვირთვა", key="single_download"):
    with st.spinner("ჩამოტვირთვა..."):
        filepath = download_csv(single_league, single_season)
        if filepath:
            df = load_csv(filepath)
            if df is not None:
                st.success(f"ჩამოტვირთულია: {len(df)} მატჩი")
                st.dataframe(df.head(10), use_container_width=True)
                init_database()
                clean_df = clean_dataframe(df)
                if "Season" not in clean_df.columns:
                    clean_df["Season"] = single_season
                db_df = prepare_for_db(clean_df)
                inserted = insert_matches(db_df)
                st.info(f"ბაზაში ჩასმულია: {inserted} მატჩი")
        else:
            st.error("ჩამოტვირთვა ვერ მოხერხდა")
