"""მოდელი - ML მოდელის ინფორმაცია და გადაწვრთნა."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import json
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

from src.config import MODEL_METADATA_PATH
from src.data.db_manager import get_model_runs

st.set_page_config(page_title="მოდელი - AIbetuchio", page_icon="🤖", layout="wide")
st.title("🤖 მოდელის ინფორმაცია")

# მეტადატა
metadata = {}
try:
    with open(str(MODEL_METADATA_PATH), "r", encoding="utf-8") as f:
        metadata = json.load(f)
except FileNotFoundError:
    st.warning("მოდელი ჯერ არ არის გაწვრთნილი. გაუშვით: python run_training.py")
    st.stop()
except Exception as e:
    st.error(f"მეტადატის წაკითხვის შეცდომა: {e}")
    st.stop()

# მეტრიკები
st.subheader("მოდელის მეტრიკები")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("მოდელის ტიპი", metadata.get("model_type", "N/A"))
with col2:
    acc = metadata.get("accuracy", 0)
    st.metric("სიზუსტე", f"{acc:.1%}")
with col3:
    ll = metadata.get("log_loss", 0)
    st.metric("Log Loss", f"{ll:.4f}")
with col4:
    st.metric("ფიჩერები", metadata.get("feature_count", 0))

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("სასწავლი მონაცემები", metadata.get("train_size", 0))
with col2:
    st.metric("სატესტო მონაცემები", metadata.get("test_size", 0))
with col3:
    trained_at = metadata.get("trained_at", "N/A")[:16]
    st.metric("გაწვრთნის თარიღი", trained_at)

# ფიჩერების მნიშვნელობა
st.markdown("---")
st.subheader("ფიჩერების მნიშვნელობა")

FEATURE_NAMES = {
    "feat_home_form_points": "სახლის ფორმა (ქულები)",
    "feat_home_form_goals_scored": "სახლის გატანილი გოლები",
    "feat_home_form_goals_conceded": "სახლის გაშვებული გოლები",
    "feat_home_form_win_rate": "სახლის მოგების სიხშირე",
    "feat_home_form_shots": "სახლის დარტყმები",
    "feat_home_form_shots_target": "სახლის დარტყმები კარში",
    "feat_home_form_corners": "სახლის კუთხურები",
    "feat_away_form_points": "სტუმრის ფორმა (ქულები)",
    "feat_away_form_goals_scored": "სტუმრის გატანილი გოლები",
    "feat_away_form_goals_conceded": "სტუმრის გაშვებული გოლები",
    "feat_away_form_win_rate": "სტუმრის მოგების სიხშირე",
    "feat_away_form_shots": "სტუმრის დარტყმები",
    "feat_away_form_shots_target": "სტუმრის დარტყმები კარში",
    "feat_away_form_corners": "სტუმრის კუთხურები",
    "feat_h2h_home_wins": "H2H სახლის მოგებები",
    "feat_h2h_draws": "H2H ფრეები",
    "feat_h2h_away_wins": "H2H სტუმრის მოგებები",
    "feat_h2h_home_goals_avg": "H2H სახლის საშ. გოლები",
    "feat_home_attack_strength": "სახლის შეტევის სიძლიერე",
    "feat_home_defense_strength": "სახლის დაცვის სიძლიერე",
    "feat_away_attack_strength": "სტუმრის შეტევის სიძლიერე",
    "feat_away_defense_strength": "სტუმრის დაცვის სიძლიერე",
    "feat_home_league_position": "სახლის პოზიცია ლიგაში",
    "feat_away_league_position": "სტუმრის პოზიცია ლიგაში",
    "feat_implied_prob_home": "კოეფ. ალბათობა (სახლი)",
    "feat_implied_prob_draw": "კოეფ. ალბათობა (ფრე)",
    "feat_implied_prob_away": "კოეფ. ალბათობა (სტუმარი)",
    "feat_odds_favorite": "კოეფ. ფავორიტი",
}

feature_importance = metadata.get("feature_importance", {})
if feature_importance:
    fi_df = pd.DataFrame([
        {"ფიჩერი": FEATURE_NAMES.get(k, k), "მნიშვნელობა": v}
        for k, v in feature_importance.items()
    ]).sort_values("მნიშვნელობა", ascending=True).tail(15)

    fig = px.bar(fi_df, x="მნიშვნელობა", y="ფიჩერი", orientation="h",
                 title="ტოპ 15 ფიჩერი", color="მნიშვნელობა",
                 color_continuous_scale="viridis")
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("ფიჩერების მნიშვნელობა ხელმისაწვდომი არ არის")

# Confusion Matrix
st.markdown("---")
st.subheader("შეცდომების მატრიცა (Confusion Matrix)")

cm = metadata.get("confusion_matrix")
if cm:
    labels = ["სტუმრის მოგ.", "ფრე", "სახლის მოგ."]
    cm_array = np.array(cm)

    fig = go.Figure(data=go.Heatmap(
        z=cm_array,
        x=labels,
        y=labels,
        text=cm_array,
        texttemplate="%{text}",
        colorscale="Blues",
    ))
    fig.update_layout(
        title="შეცდომების მატრიცა",
        xaxis_title="პროგნოზი",
        yaxis_title="რეალური",
        width=500, height=500,
    )
    st.plotly_chart(fig)

# კლასიფიკაციის ანგარიში
st.markdown("---")
st.subheader("კლასიფიკაციის ანგარიში")

report = metadata.get("classification_report", {})
if report:
    report_data = []
    label_map = {"A": "სტუმრის მოგება", "D": "ფრე", "H": "სახლის მოგება"}
    for label in ["A", "D", "H"]:
        if label in report:
            r = report[label]
            report_data.append({
                "კლასი": label_map[label],
                "სიზუსტე (Precision)": f"{r.get('precision', 0):.3f}",
                "გამოვლენა (Recall)": f"{r.get('recall', 0):.3f}",
                "F1-ქულა": f"{r.get('f1-score', 0):.3f}",
                "რაოდენობა": r.get("support", 0),
            })
    if report_data:
        st.dataframe(pd.DataFrame(report_data), use_container_width=True)

# პარამეტრები
st.markdown("---")
st.subheader("მოდელის პარამეტრები")
params = metadata.get("parameters", {})
if params:
    st.json(params)
else:
    st.info("პარამეტრები ხელმისაწვდომი არ არის")

# ფიჩერების სია
st.markdown("---")
with st.expander("ყველა ფიჩერის სია"):
    features = metadata.get("feature_columns", [])
    for i, feat in enumerate(features, 1):
        display_name = FEATURE_NAMES.get(feat, feat)
        st.write(f"{i}. {display_name}")

# გაწვრთნის ისტორია
st.markdown("---")
st.subheader("გაწვრთნის ისტორია")

model_runs = get_model_runs()
if not model_runs.empty:
    runs_display = model_runs.rename(columns={
        "run_date": "თარიღი", "model_type": "მოდელი", "accuracy": "სიზუსტე",
        "log_loss": "Log Loss", "train_size": "სასწავლი", "test_size": "სატესტო",
    })
    show_cols = ["თარიღი", "მოდელი", "სიზუსტე", "Log Loss", "სასწავლი", "სატესტო"]
    available = [c for c in show_cols if c in runs_display.columns]
    st.dataframe(runs_display[available], use_container_width=True)

    if len(model_runs) > 1:
        fig = px.line(model_runs.sort_values("run_date"),
                      x="run_date", y="accuracy",
                      title="სიზუსტის ისტორია", markers=True,
                      labels={"run_date": "თარიღი", "accuracy": "სიზუსტე"})
        st.plotly_chart(fig, use_container_width=True)

# გადაწვრთნის ღილაკი
st.markdown("---")
st.subheader("მოდელის გადაწვრთნა")
st.warning("გადაწვრთნა შეცვლის მიმდინარე მოდელს")

if st.button("მოდელის გადაწვრთნა", type="primary"):
    with st.spinner("მოდელი იწვრთნება... (შეიძლება რამდენიმე წუთი)"):
        try:
            from src.ml.trainer import MatchPredictor
            trainer = MatchPredictor()
            results = trainer.train()
            if results:
                st.success(
                    f"მოდელი გადაწვრთნილია!\n"
                    f"სიზუსტე: {results['accuracy']:.1%}\n"
                    f"Log Loss: {results['log_loss']:.4f}"
                )
                st.rerun()
            else:
                st.error("გაწვრთნა ვერ მოხერხდა")
        except Exception as e:
            st.error(f"შეცდომა: {e}")
