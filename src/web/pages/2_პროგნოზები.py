"""პროგნოზები - მატჩების პროგნოზები ალბათობებით."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import streamlit as st
import pandas as pd
import plotly.express as px

from src.ml.predictor import Predictor
from src.config import LEAGUES

st.set_page_config(page_title="პროგნოზები - AIbetuchio", page_icon="🎯", layout="wide")
st.title("🎯 პროგნოზები")

# ფილტრები
col1, col2 = st.columns(2)
with col1:
    league_display = {"ყველა ლიგა": None}
    for code, name in LEAGUES.items():
        league_display[f"{name} ({code})"] = code
    selected_league = st.selectbox("ლიგა", options=list(league_display.keys()))
    division = league_display[selected_league]

with col2:
    num_predictions = st.slider("პროგნოზების რაოდენობა", 10, 100, 30)

RESULT_MAP = {"H": "სახლის მოგება", "D": "ფრე", "A": "სტუმრის მოგება"}

try:
    predictor = Predictor()
    if not predictor.is_ready():
        st.warning("მოდელი ჯერ არ არის გაწვრთნილი. გაუშვით: python run_training.py")
        st.stop()

    predictions = predictor.get_latest_predictions(n=num_predictions, division=division)

    if predictions.empty:
        st.info("პროგნოზები ვერ მოიძებნა")
        st.stop()

    # ცხრილი
    st.subheader(f"ბოლო {len(predictions)} პროგნოზი")

    display_df = predictions.copy()
    display_df["სახლის %"] = (display_df.get("prob_H", pd.Series(dtype=float)) * 100).round(1)
    display_df["ფრე %"] = (display_df.get("prob_D", pd.Series(dtype=float)) * 100).round(1)
    display_df["სტუმრის %"] = (display_df.get("prob_A", pd.Series(dtype=float)) * 100).round(1)
    display_df["ნდობა %"] = (display_df.get("confidence", pd.Series(dtype=float)) * 100).round(1)
    display_df["პროგნოზი"] = display_df.get("predicted", pd.Series(dtype=str)).map(RESULT_MAP)
    display_df["შედეგი"] = display_df.get("FTR", pd.Series(dtype=str)).map(RESULT_MAP)
    display_df["ლიგა"] = display_df.get("Div", pd.Series(dtype=str)).map(LEAGUES)
    display_df["სწორია?"] = display_df.get("is_correct", pd.Series(dtype=int)).map({1: "✅", 0: "❌"})

    show_cols = ["Date", "HomeTeam", "AwayTeam", "ლიგა", "პროგნოზი",
                 "სახლის %", "ფრე %", "სტუმრის %", "ნდობა %", "შედეგი", "სწორია?"]
    available_cols = [c for c in show_cols if c in display_df.columns]
    final_df = display_df[available_cols].rename(columns={
        "Date": "თარიღი", "HomeTeam": "სახლის გუნდი", "AwayTeam": "სტუმარი გუნდი",
    })

    st.dataframe(final_df, use_container_width=True, height=600)

    # სტატისტიკა
    st.markdown("---")
    st.subheader("პროგნოზების სტატისტიკა")

    col1, col2, col3 = st.columns(3)

    with col1:
        if "is_correct" in predictions.columns:
            correct = predictions["is_correct"].sum()
            total = len(predictions)
            st.metric("სიზუსტე", f"{correct/total*100:.1f}%", f"{correct}/{total}")

    with col2:
        if "predicted" in predictions.columns:
            pred_dist = predictions["predicted"].value_counts()
            st.write("პროგნოზების განაწილება:")
            for result, count in pred_dist.items():
                label = RESULT_MAP.get(result, result)
                st.write(f"  {label}: {count} ({count/len(predictions)*100:.1f}%)")

    with col3:
        if "confidence" in predictions.columns:
            avg_conf = predictions["confidence"].mean()
            st.metric("საშუალო ნდობა", f"{avg_conf*100:.1f}%")

    # ალბათობების განაწილება
    if all(c in predictions.columns for c in ["prob_H", "prob_D", "prob_A"]):
        st.subheader("ალბათობების განაწილება")
        prob_data = pd.melt(
            predictions[["prob_H", "prob_D", "prob_A"]],
            var_name="შედეგი", value_name="ალბათობა"
        )
        prob_data["შედეგი"] = prob_data["შედეგი"].map({
            "prob_H": "სახლის მოგება", "prob_D": "ფრე", "prob_A": "სტუმრის მოგება"
        })
        fig = px.histogram(prob_data, x="ალბათობა", color="შედეგი",
                          barmode="overlay", nbins=30,
                          title="მოდელის ალბათობების განაწილება")
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"შეცდომა: {e}")
    st.info("გაუშვით ჯერ: python setup_data.py და python run_training.py")
