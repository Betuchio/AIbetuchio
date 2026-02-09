"""Telegram შეტყობინებების ფორმატირება."""
import pandas as pd
from src.utils.helpers import result_to_label


def format_prediction(pred: dict) -> str:
    """ერთი პროგნოზის ფორმატირება."""
    prob_h = pred.get("prob_home", 0) * 100
    prob_d = pred.get("prob_draw", 0) * 100
    prob_a = pred.get("prob_away", 0) * 100
    confidence = pred.get("confidence", 0) * 100
    predicted = result_to_label(pred.get("predicted_result", ""))

    text = (
        f"⚽ *{pred.get('home_team', '')} vs {pred.get('away_team', '')}*\n"
        f"📅 {pred.get('date', '')}\n"
        f"🏆 {pred.get('division', '')}\n"
        f"\n"
        f"📊 *პროგნოზი: {predicted}*\n"
        f"🎯 Confidence: {confidence:.1f}%\n"
        f"\n"
        f"Home: {prob_h:.1f}% | Draw: {prob_d:.1f}% | Away: {prob_a:.1f}%\n"
    )

    if pred.get("odds_home"):
        text += (
            f"\n💰 Odds: {pred.get('odds_home', 0):.2f} | "
            f"{pred.get('odds_draw', 0):.2f} | "
            f"{pred.get('odds_away', 0):.2f}\n"
        )

    return text


def format_predictions_list(predictions: pd.DataFrame) -> str:
    """პროგნოზების სიის ფორმატირება."""
    if predictions.empty:
        return "პროგნოზები ვერ მოიძებნა"

    lines = ["📊 *პროგნოზები*\n"]

    for _, row in predictions.iterrows():
        predicted = row.get("predicted", "")
        confidence = row.get("confidence", 0) * 100

        emoji = {"H": "🏠", "D": "🤝", "A": "✈️"}.get(predicted, "❓")

        line = (
            f"{emoji} *{row.get('HomeTeam', '')} vs {row.get('AwayTeam', '')}*\n"
            f"   → {result_to_label(predicted)} ({confidence:.0f}%)\n"
        )
        lines.append(line)

    return "\n".join(lines)


def format_value_bets(vb_df: pd.DataFrame) -> str:
    """Value bet-ების ფორმატირება."""
    if vb_df.empty:
        return "💰 Value bet-ები ამჟამად არ არის"

    lines = ["💰 *Value Bets*\n"]

    for _, row in vb_df.head(10).iterrows():
        edge = row.get("edge_pct", 0)
        kelly = row.get("kelly_pct", 0)

        line = (
            f"⚽ *{row.get('home_team', '')} vs {row.get('away_team', '')}*\n"
            f"   💎 {row.get('bet_type', '')} @ {row.get('odds', 0):.2f}\n"
            f"   📈 Edge: {edge:.1f}% | Kelly: {kelly:.1f}%\n"
        )
        lines.append(line)

    return "\n".join(lines)


def format_standings(standings: pd.DataFrame) -> str:
    """ლიგის ცხრილის ფორმატირება."""
    if standings.empty:
        return "ცხრილი ვერ მოიძებნა"

    lines = ["🏆 *ლიგის ცხრილი*\n"]
    lines.append("`# | Team          | P  | W | D | L | Pts`")
    lines.append("`" + "-" * 42 + "`")

    for idx, row in standings.head(20).iterrows():
        team = str(row.get("Team", ""))[:13].ljust(13)
        line = (
            f"`{idx:2d}| {team} | "
            f"{row.get('P', 0):2d} | "
            f"{row.get('W', 0):1d} | "
            f"{row.get('D', 0):1d} | "
            f"{row.get('L', 0):1d} | "
            f"{row.get('Pts', 0):3d}`"
        )
        lines.append(line)

    return "\n".join(lines)


def format_h2h(h2h_matches: pd.DataFrame, team1: str, team2: str) -> str:
    """H2H ფორმატირება."""
    if h2h_matches.empty:
        return f"პირისპირ მატჩები ვერ მოიძებნა: {team1} vs {team2}"

    lines = [f"⚔️ *{team1} vs {team2}*\n"]
    lines.append(f"სულ შეხვედრები: {len(h2h_matches)}\n")

    for _, row in h2h_matches.tail(5).iterrows():
        score = f"{int(row.get('fthg', 0))}-{int(row.get('ftag', 0))}"
        lines.append(
            f"📅 {row.get('date', '')} | "
            f"{row.get('home_team', '')} {score} {row.get('away_team', '')}"
        )

    return "\n".join(lines)


def format_roi_summary(bets: pd.DataFrame) -> str:
    """ROI შეჯამების ფორმატირება."""
    if bets.empty:
        return "📈 ფსონები ჯერ არ არის ჩანიშნული"

    settled = bets[bets["result"].isin(["won", "lost"])]
    if settled.empty:
        return "📈 შეფასებული ფსონები ჯერ არ არის"

    total = len(settled)
    wins = len(settled[settled["result"] == "won"])
    profit = settled["profit"].sum()
    staked = settled["stake"].sum()
    roi = (profit / staked * 100) if staked > 0 else 0

    return (
        f"📈 *ROI შეჯამება*\n\n"
        f"🎲 სულ ფსონები: {total}\n"
        f"✅ მოგებული: {wins}\n"
        f"❌ წაგებული: {total - wins}\n"
        f"📊 Win Rate: {wins/total*100:.1f}%\n"
        f"💰 Profit: {profit:+.2f} units\n"
        f"📈 ROI: {roi:+.1f}%"
    )
