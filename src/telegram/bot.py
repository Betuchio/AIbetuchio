"""Telegram ბოტის მთავარი მოდული."""
import os
from dotenv import load_dotenv
from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler, filters,
)

from src.telegram.commands import (
    cmd_start, cmd_today, cmd_weekend, cmd_predict,
    cmd_valuebets, cmd_league, cmd_h2h, cmd_roi, cmd_leagues,
)
from src.utils.logger import get_logger

log = get_logger(__name__)

# .env ფაილის ჩატვირთვა
load_dotenv()

# გამოწერილი მომხმარებლები (მეხსიერებაში)
subscribers = set()


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(cmd_start(), parse_mode="Markdown")


async def today_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(cmd_today(), parse_mode="Markdown")


async def weekend_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(cmd_weekend(), parse_mode="Markdown")


async def predict_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    team = " ".join(context.args) if context.args else ""
    await update.message.reply_text(cmd_predict(team), parse_mode="Markdown")


async def valuebets_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(cmd_valuebets(), parse_mode="Markdown")


async def league_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = context.args[0] if context.args else ""
    await update.message.reply_text(cmd_league(code), parse_mode="Markdown")


async def h2h_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args) if context.args else ""
    await update.message.reply_text(cmd_h2h(text), parse_mode="Markdown")


async def roi_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(cmd_roi(), parse_mode="Markdown")


async def leagues_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(cmd_leagues(), parse_mode="Markdown")


async def subscribe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers.add(chat_id)
    await update.message.reply_text(
        "✅ გამოწერილია ყოველდღიური შეტყობინებები!\n"
        "ყოველ დილას მიიღებთ დღის პროგნოზებს."
    )


async def unsubscribe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers.discard(chat_id)
    await update.message.reply_text("❌ გამოწერა გაუქმებულია")


async def unknown_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ უცნობი ბრძანება. /start - ბრძანებების სია"
    )


async def post_init(application: Application):
    """ბოტის ბრძანებების მენიუს დაყენება."""
    commands = [
        BotCommand("start", "მისასალმებელი შეტყობინება"),
        BotCommand("today", "დღევანდელი პროგნოზები"),
        BotCommand("weekend", "შაბათ-კვირის პროგნოზები"),
        BotCommand("predict", "გუნდის პროგნოზი"),
        BotCommand("valuebets", "Value bet-ები"),
        BotCommand("league", "ლიგის ცხრილი"),
        BotCommand("h2h", "Head-to-Head"),
        BotCommand("roi", "ROI შეჯამება"),
        BotCommand("leagues", "ლიგების სია"),
        BotCommand("subscribe", "ყოველდღიური შეტყობინებები"),
    ]
    await application.bot.set_my_commands(commands)
    log.info("ბოტის ბრძანებები დაყენებულია")


def create_bot(token: str) -> Application:
    """ბოტის აპლიკაციის შექმნა."""
    app = Application.builder().token(token).post_init(post_init).build()

    # ბრძანებების რეგისტრაცია
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("today", today_handler))
    app.add_handler(CommandHandler("weekend", weekend_handler))
    app.add_handler(CommandHandler("predict", predict_handler))
    app.add_handler(CommandHandler("valuebets", valuebets_handler))
    app.add_handler(CommandHandler("league", league_handler))
    app.add_handler(CommandHandler("h2h", h2h_handler))
    app.add_handler(CommandHandler("roi", roi_handler))
    app.add_handler(CommandHandler("leagues", leagues_handler))
    app.add_handler(CommandHandler("subscribe", subscribe_handler))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe_handler))

    # უცნობი ბრძანებები
    app.add_handler(MessageHandler(filters.COMMAND, unknown_handler))

    return app
