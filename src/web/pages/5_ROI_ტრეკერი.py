"""ROI ტრეკერი - ფსონების აღრიცხვა და მოგება/ზარალი."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from src.data.db_manager import get_bets, insert_bet, update_bet_result

st.set_page_config(page_title="ROI ტრეკერი - AIbetuchio", page_icon="📈", layout="wide")
st.title("📈 ROI ტრეკერი")

# ახალი ფსონის დამატება
st.subheader("ახალი ფსონის ჩანიშვნა")

with st.form("new_bet"):
    col1, col2, col3 = st.columns(3)
    with col1:
        date = st.date_input("თარიღი", value=datetime.now())
        home_team = st.text_input("სახლის გუნდი")
    with col2:
        away_team = st.text_input("სტუმარი გუნდი")
        bet_type = st.selectbox("ფსონის ტიპი", [
            "სახლის მოგება", "ფრე", "სტუმრის მოგება",
            "სულ გოლი 2.5-ზე მეტი", "სულ გოლი 2.5-ზე ნაკლები",
            "ორივე გაიტანს - კი", "ორივე გაიტანს - არა",
        ])
    with col3:
        odds = st.number_input("კოეფიციენტი", min_value=1.01, value=2.0, step=0.01)
        stake = st.number_input("ფსონის ზომა (ერთეული)", min_value=0.1, value=1.0, step=0.1)

    submitted = st.form_submit_button("ფსონის დამატება")
    if submitted and home_team and away_team:
        bet = {
            "prediction_id": None,
            "date": date.strftime("%Y-%m-%d"),
            "home_team": home_team,
            "away_team": away_team,
            "bet_type": bet_type,
            "odds": odds,
            "stake": stake,
            "result": "pending",
            "profit": 0,
        }
        insert_bet(bet)
        st.success(f"ფსონი დამატებულია: {home_team} vs {away_team}")
        st.rerun()

# ფსონების სია
st.markdown("---")
bets = get_bets()

if bets.empty:
    st.info("ფსონები ჯერ არ არის ჩანიშნული")
    st.stop()

# შედეგის განახლება
st.subheader("მომლოდინე ფსონების შეფასება")
pending_bets = bets[bets["result"] == "pending"]

if not pending_bets.empty:
    for _, bet in pending_bets.iterrows():
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.write(f"**{bet['home_team']} vs {bet['away_team']}** ({bet['bet_type']}) @ {bet['odds']}")
        with col2:
            if st.button("მოიგო ✅", key=f"won_{bet['id']}"):
                update_bet_result(bet["id"], "won")
                st.rerun()
        with col3:
            if st.button("წააგო ❌", key=f"lost_{bet['id']}"):
                update_bet_result(bet["id"], "lost")
                st.rerun()
else:
    st.info("ყველა ფსონი შეფასებულია")

# სტატისტიკა
st.markdown("---")
st.subheader("სტატისტიკა")

settled = bets[bets["result"].isin(["won", "lost"])]

if not settled.empty:
    col1, col2, col3, col4, col5 = st.columns(5)

    total_bets = len(settled)
    wins = len(settled[settled["result"] == "won"])
    losses = len(settled[settled["result"] == "lost"])
    total_staked = settled["stake"].sum()
    total_profit = settled["profit"].sum()
    roi = (total_profit / total_staked * 100) if total_staked > 0 else 0

    with col1:
        st.metric("სულ ფსონები", total_bets)
    with col2:
        st.metric("მოგ / წაგ", f"{wins} / {losses}")
    with col3:
        st.metric("მოგების სიხშირე", f"{wins/total_bets*100:.1f}%")
    with col4:
        st.metric("მოგება", f"{total_profit:+.2f} ერთ.")
    with col5:
        st.metric("ROI", f"{roi:+.1f}%")

    # კუმულატიური P&L გრაფიკი
    settled_sorted = settled.sort_values("date")
    settled_sorted["კუმულატიური"] = settled_sorted["profit"].cumsum()
    settled_sorted["ფსონი #"] = range(1, len(settled_sorted) + 1)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=settled_sorted["ფსონი #"],
        y=settled_sorted["კუმულატიური"],
        mode="lines+markers",
        name="მოგება/ზარალი",
        line=dict(color="green" if total_profit >= 0 else "red"),
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(
        title="კუმულატიური მოგება/ზარალი",
        xaxis_title="ფსონის ნომერი",
        yaxis_title="მოგება (ერთეულები)",
    )
    st.plotly_chart(fig, use_container_width=True)

    # ფსონის ტიპის მიხედვით
    st.subheader("ფსონის ტიპის მიხედვით")
    by_type = settled.groupby("bet_type").agg(
        ფსონები=("id", "count"),
        მოგებული=("result", lambda x: (x == "won").sum()),
        მოგება=("profit", "sum"),
        საშ_კოეფ=("odds", "mean"),
    ).reset_index()
    by_type = by_type.rename(columns={"bet_type": "ფსონის ტიპი", "საშ_კოეფ": "საშ. კოეფ."})
    by_type["მოგების %"] = (by_type["მოგებული"] / by_type["ფსონები"] * 100).round(1)
    by_type["ROI %"] = (by_type["მოგება"] / by_type["ფსონები"] * 100).round(1)
    st.dataframe(by_type, use_container_width=True)

# სრული ცხრილი
st.markdown("---")
st.subheader("ყველა ფსონი")
bets_display = bets.rename(columns={
    "id": "#", "date": "თარიღი", "home_team": "სახლის გუნდი",
    "away_team": "სტუმარი გუნდი", "bet_type": "ფსონის ტიპი",
    "odds": "კოეფ.", "stake": "ფსონი", "result": "შედეგი", "profit": "მოგება",
})
RESULT_MAP = {"won": "მოიგო ✅", "lost": "წააგო ❌", "pending": "მოლოდინში ⏳"}
if "შედეგი" in bets_display.columns:
    bets_display["შედეგი"] = bets_display["შედეგი"].map(RESULT_MAP).fillna(bets_display["შედეგი"])
show_cols = ["#", "თარიღი", "სახლის გუნდი", "სტუმარი გუნდი", "ფსონის ტიპი",
             "კოეფ.", "ფსონი", "შედეგი", "მოგება"]
available = [c for c in show_cols if c in bets_display.columns]
st.dataframe(bets_display[available], use_container_width=True)
