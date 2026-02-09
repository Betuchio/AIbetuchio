"""ღირებული ფსონები - Value bet-ების რეკომენდაციები."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import streamlit as st
import pandas as pd
import plotly.express as px

from src.ml.predictor import Predictor
from src.ml.value_bets import find_value_bets, analyze_value_bets_performance
from src.config import LEAGUES, MIN_EDGE_THRESHOLD

st.set_page_config(page_title="ღირებული ფსონები - AIbetuchio", page_icon="💰", layout="wide")
st.title("💰 ღირებული ფსონები (Value Bets)")

st.markdown("""
**ღირებული ფსონი** = მოდელის ალბათობა > ბუკმეკერის ნაგულისხმევი ალბათობა + ზღვარი

`ზღვარი (edge) = მოდელის_ალბათობა - ბუკმეკერის_ალბათობა`
""")

# ფილტრები
col1, col2, col3 = st.columns(3)
with col1:
    min_edge = st.slider("მინ. ზღვარი (Edge) %", 1, 20, int(MIN_EDGE_THRESHOLD * 100)) / 100
with col2:
    league_display = {"ყველა ლიგა": None}
    for code, name in LEAGUES.items():
        league_display[f"{name} ({code})"] = code
    selected_league = st.selectbox("ლიგა", options=list(league_display.keys()))
    division = league_display[selected_league]
with col3:
    num_matches = st.slider("მატჩების რაოდენობა", 20, 200, 50)

BET_TYPE_MAP = {"Home Win": "სახლის მოგება", "Draw": "ფრე", "Away Win": "სტუმრის მოგება"}

try:
    predictor = Predictor()
    if not predictor.is_ready():
        st.warning("მოდელი ჯერ არ არის გაწვრთნილი. გაუშვით: python run_training.py")
        st.stop()

    predictions = predictor.get_latest_predictions(n=num_matches, division=division)
    if predictions.empty:
        st.info("პროგნოზები ვერ მოიძებნა")
        st.stop()

    value_bets = find_value_bets(predictions, min_edge=min_edge)

    if value_bets.empty:
        st.info(f"ღირებული ფსონები ვერ მოიძებნა (მინ. ზღვარი: {min_edge*100:.1f}%)")
        st.stop()

    # მეტრიკები
    st.subheader(f"ნაპოვნია {len(value_bets)} ღირებული ფსონი")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("ღირებული ფსონები", len(value_bets))
    with col2:
        st.metric("საშ. ზღვარი", f"{value_bets['edge_pct'].mean():.1f}%")
    with col3:
        st.metric("მაქს. ზღვარი", f"{value_bets['edge_pct'].max():.1f}%")
    with col4:
        st.metric("საშ. კოეფიციენტი", f"{value_bets['odds'].mean():.2f}")

    # ცხრილი
    st.markdown("---")
    display_vb = value_bets.copy()
    display_vb["ფსონის ტიპი"] = display_vb["bet_type"].map(BET_TYPE_MAP)
    display_vb["ლიგა"] = display_vb["division"].map(LEAGUES)
    display_vb["რეალური შედეგი"] = display_vb["actual_result"].map(
        {"H": "სახლის მოგება", "D": "ფრე", "A": "სტუმრის მოგება"})

    display_vb = display_vb.rename(columns={
        "date": "თარიღი", "home_team": "სახლის გუნდი", "away_team": "სტუმარი გუნდი",
        "odds": "კოეფ.", "model_prob": "მოდელის ალბ.", "implied_prob": "ბუკმ. ალბ.",
        "edge_pct": "ზღვარი %", "kelly_pct": "Kelly %", "expected_value": "მოსალ. ღირებულება",
    })

    show_cols = ["თარიღი", "სახლის გუნდი", "სტუმარი გუნდი", "ლიგა", "ფსონის ტიპი",
                 "კოეფ.", "მოდელის ალბ.", "ბუკმ. ალბ.", "ზღვარი %",
                 "Kelly %", "მოსალ. ღირებულება", "რეალური შედეგი"]
    available = [c for c in show_cols if c in display_vb.columns]
    st.dataframe(display_vb[available], use_container_width=True, height=500)

    # ისტორიული წარმადობა
    st.markdown("---")
    st.subheader("ისტორიული წარმადობა")

    perf = analyze_value_bets_performance(value_bets)
    if perf:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("მოგების სიხშირე", f"{perf['win_rate']}%")
        with col2:
            st.metric("ROI", f"{perf['roi']}%")
        with col3:
            st.metric("მოგება", f"{perf['total_profit']:+.2f} ერთ.")
        with col4:
            st.metric("საშ. ზღვარი", f"{perf['avg_edge']}%")

    # ზღვრის განაწილება
    st.subheader("ზღვრის (Edge) განაწილება")
    plot_vb = value_bets.copy()
    plot_vb["ფსონის ტიპი"] = plot_vb["bet_type"].map(BET_TYPE_MAP)
    fig = px.histogram(plot_vb, x="edge_pct", nbins=20,
                       title="ზღვრის % განაწილება", color="ფსონის ტიპი",
                       labels={"edge_pct": "ზღვარი %", "count": "რაოდენობა"})
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"შეცდომა: {e}")
    st.info("გაუშვით ჯერ: python setup_data.py და python run_training.py")
