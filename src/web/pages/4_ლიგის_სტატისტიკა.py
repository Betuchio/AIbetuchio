"""ლიგის სტატისტიკა - ცხრილი, ფორმა, პირისპირ."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import streamlit as st
import pandas as pd

from src.data.db_manager import get_all_matches
from src.config import LEAGUES

st.set_page_config(page_title="ლიგის სტატისტიკა - AIbetuchio", page_icon="🏆", layout="wide")
st.title("🏆 ლიგის სტატისტიკა")

# ლიგის არჩევა
league_display = {}
for code, name in LEAGUES.items():
    league_display[f"{name} ({code})"] = code
selected_label = st.selectbox("აირჩიეთ ლიგა", options=list(league_display.keys()))
selected_code = league_display[selected_label]

matches = get_all_matches(division=selected_code)

if matches.empty:
    st.warning("მატჩები ვერ მოიძებნა ამ ლიგისთვის")
    st.stop()

st.info(f"სულ მატჩები: {len(matches)}")


def compute_standings(df):
    teams = set(df["home_team"].unique()) | set(df["away_team"].unique())
    table = []
    for team in teams:
        home = df[df["home_team"] == team]
        away = df[df["away_team"] == team]
        hw = len(home[home["ftr"] == "H"])
        hd = len(home[home["ftr"] == "D"])
        hl = len(home[home["ftr"] == "A"])
        aw = len(away[away["ftr"] == "A"])
        ad = len(away[away["ftr"] == "D"])
        al = len(away[away["ftr"] == "H"])
        played = len(home) + len(away)
        wins = hw + aw
        draws = hd + ad
        losses = hl + al
        gf = int((home["fthg"].sum() or 0) + (away["ftag"].sum() or 0))
        ga = int((home["ftag"].sum() or 0) + (away["fthg"].sum() or 0))
        gd = gf - ga
        points = wins * 3 + draws
        table.append({
            "გუნდი": team, "მატჩი": played, "მოგ": wins, "ფრე": draws,
            "წაგ": losses, "გატ": gf, "გაშ": ga, "სხვაობა": gd, "ქულა": points,
        })
    table_df = pd.DataFrame(table)
    table_df = table_df.sort_values(["ქულა", "სხვაობა", "გატ"], ascending=[False, False, False])
    table_df = table_df.reset_index(drop=True)
    table_df.index += 1
    table_df.index.name = "#"
    return table_df


# ლიგის ცხრილი
st.subheader("ლიგის ცხრილი")
standings = compute_standings(matches)
st.dataframe(standings, use_container_width=True)

# გუნდის ფორმა
st.markdown("---")
st.subheader("გუნდის ფორმა")

teams = sorted(set(matches["home_team"].unique()) | set(matches["away_team"].unique()))
selected_team = st.selectbox("აირჩიეთ გუნდი", options=teams)

if selected_team:
    team_home = matches[matches["home_team"] == selected_team]
    team_away = matches[matches["away_team"] == selected_team]

    all_team = pd.concat([
        team_home[["date", "home_team", "away_team", "fthg", "ftag", "ftr"]],
        team_away[["date", "home_team", "away_team", "fthg", "ftag", "ftr"]],
    ]).sort_values("date").tail(10)

    results = []
    for _, row in all_team.iterrows():
        is_home = row["home_team"] == selected_team
        opponent = row["away_team"] if is_home else row["home_team"]
        gs = row["fthg"] if is_home else row["ftag"]
        gc = row["ftag"] if is_home else row["fthg"]
        ftr = row["ftr"]
        if (is_home and ftr == "H") or (not is_home and ftr == "A"):
            result = "მოგება"
        elif ftr == "D":
            result = "ფრე"
        else:
            result = "წაგება"
        venue = "სახლში" if is_home else "გასტანაზე"
        results.append({
            "თარიღი": row["date"],
            "მოწინააღმდეგე": opponent,
            "ადგილი": venue,
            "ანგარიში": f"{int(gs)}-{int(gc)}",
            "შედეგი": result,
        })

    st.dataframe(pd.DataFrame(results), use_container_width=True)

    # ფორმის მეტრიკები
    col1, col2, col3, col4 = st.columns(4)
    form = [r["შედეგი"] for r in results[-5:]]
    form_short = [{"მოგება": "მ", "ფრე": "ფ", "წაგება": "წ"}[f] for f in form]
    with col1:
        st.metric("ბოლო 5", " ".join(form_short))
    with col2:
        points = sum(3 if r == "მოგება" else 1 if r == "ფრე" else 0 for r in form)
        st.metric("ქულები (5-დან 15)", points)
    with col3:
        goals_scored = sum(int(r["ანგარიში"].split("-")[0]) for r in results[-5:])
        st.metric("გატანილი გოლები", goals_scored)
    with col4:
        goals_conceded = sum(int(r["ანგარიში"].split("-")[1]) for r in results[-5:])
        st.metric("გაშვებული გოლები", goals_conceded)

# პირისპირ (Head-to-Head)
st.markdown("---")
st.subheader("პირისპირ შედარება")
col1, col2 = st.columns(2)
with col1:
    team1 = st.selectbox("პირველი გუნდი", options=teams, key="h2h_team1")
with col2:
    team2 = st.selectbox("მეორე გუნდი", options=teams, key="h2h_team2", index=min(1, len(teams)-1))

if team1 and team2 and team1 != team2:
    h2h = matches[
        ((matches["home_team"] == team1) & (matches["away_team"] == team2)) |
        ((matches["home_team"] == team2) & (matches["away_team"] == team1))
    ].sort_values("date")

    if h2h.empty:
        st.info("პირისპირ მატჩები ვერ მოიძებნა")
    else:
        st.write(f"სულ შეხვედრები: {len(h2h)}")
        h2h_display = h2h[["date", "home_team", "away_team", "fthg", "ftag", "ftr"]].tail(10)
        h2h_display = h2h_display.rename(columns={
            "date": "თარიღი", "home_team": "სახლის გუნდი", "away_team": "სტუმარი გუნდი",
            "fthg": "სახლის გოლი", "ftag": "სტუმრის გოლი", "ftr": "შედეგი",
        })
        st.dataframe(h2h_display, use_container_width=True)

        t1_wins = len(h2h[
            ((h2h["home_team"] == team1) & (h2h["ftr"] == "H")) |
            ((h2h["away_team"] == team1) & (h2h["ftr"] == "A"))
        ])
        t2_wins = len(h2h[
            ((h2h["home_team"] == team2) & (h2h["ftr"] == "H")) |
            ((h2h["away_team"] == team2) & (h2h["ftr"] == "A"))
        ])
        draws = len(h2h[h2h["ftr"] == "D"])

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(f"{team1} - მოგებები", t1_wins)
        with col2:
            st.metric("ფრეები", draws)
        with col3:
            st.metric(f"{team2} - მოგებები", t2_wins)
