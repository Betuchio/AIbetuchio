"""მთავარი პანელი - დღევანდელი პროგნოზები და მეტრიკები."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

from src.data.db_manager import get_all_matches, get_predictions, get_bets, get_model_runs
from src.ml.predictor import Predictor
from src.config import LEAGUES

st.set_page_config(page_title="მთავარი პანელი - AIbetuchio", page_icon="📊", layout="wide")
st.title("📊 მთავარი პანელი")

# მეტრიკები
col1, col2, col3, col4 = st.columns(4)

matches = get_all_matches()
predictions = get_predictions()
bets = get_bets()
model_runs = get_model_runs()

with col1:
    st.metric("სულ მატჩები", len(matches))

with col2:
    st.metric("პროგნოზები", len(predictions))

with col3:
    if not predictions.empty and "is_correct" in predictions.columns:
        correct = predictions["is_correct"].sum()
        total = predictions["is_correct"].count()
        accuracy = correct / total * 100 if total > 0 else 0
        st.metric("სიზუსტე", f"{accuracy:.1f}%")
    else:
        st.metric("სიზუსტე", "N/A")

with col4:
    if not bets.empty and "profit" in bets.columns:
        total_profit = bets["profit"].sum()
        st.metric("მოგება/ზარალი", f"{total_profit:+.2f} ერთ.")
    else:
        st.metric("მოგება/ზარალი", "0.00 ერთ.")

st.markdown("---")

# მოდელის სტატუსი
if not model_runs.empty:
    latest = model_runs.iloc[0]
    st.success(f"მოდელი: {latest.get('model_type', 'N/A')} | "
               f"სიზუსტე: {latest.get('accuracy', 0):.1%} | "
               f"გაწვრთნილია: {latest.get('run_date', 'N/A')}")
else:
    st.warning("მოდელი ჯერ არ არის გაწვრთნილი. გაუშვით: python run_training.py")

# ბოლო პროგნოზები
st.subheader("ბოლო პროგნოზები")
try:
    predictor = Predictor()
    if predictor.is_ready():
        latest_preds = predictor.get_latest_predictions(n=10)
        if not latest_preds.empty:
            display_df = latest_preds.copy()
            rename_map = {
                "Date": "თარიღი", "HomeTeam": "სახლის გუნდი",
                "AwayTeam": "სტუმარი გუნდი", "Div": "ლიგა",
                "predicted": "პროგნოზი", "confidence": "ნდობა", "FTR": "შედეგი",
            }
            cols = [c for c in rename_map if c in display_df.columns]
            display_df = display_df[cols].rename(columns=rename_map)
            if "ნდობა" in display_df.columns:
                display_df["ნდობა"] = (display_df["ნდობა"] * 100).round(1).astype(str) + "%"
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("პროგნოზები ჯერ არ არის")
    else:
        st.info("მოდელი ჩატვირთვის მოლოდინშია")
except Exception:
    st.info("პროგნოზები ხელმისაწვდომი იქნება მოდელის გაწვრთნის შემდეგ")

# ლიგების მიხედვით მატჩების რაოდენობა
st.subheader("მატჩები ლიგების მიხედვით")
if not matches.empty and "division" in matches.columns:
    league_counts = matches["division"].value_counts().reset_index()
    league_counts.columns = ["division", "count"]
    league_counts["ლიგა"] = league_counts["division"].map(LEAGUES)

    fig = px.bar(league_counts, x="ლიგა", y="count",
                 title="მატჩების რაოდენობა ლიგების მიხედვით",
                 color="count", color_continuous_scale="viridis",
                 labels={"count": "მატჩები", "ლიგა": "ლიგა"})
    st.plotly_chart(fig, use_container_width=True)

# ROI გრაფიკი
if not bets.empty and "profit" in bets.columns and "date" in bets.columns:
    st.subheader("მოგება/ზარალის დინამიკა")
    bets_sorted = bets.sort_values("date")
    bets_sorted["კუმულატიური"] = bets_sorted["profit"].cumsum()

    fig2 = px.line(bets_sorted, x="date", y="კუმულატიური",
                   title="კუმულატიური მოგება/ზარალი",
                   labels={"date": "თარიღი", "კუმულატიური": "მოგება (ერთეულები)"})
    fig2.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig2, use_container_width=True)
