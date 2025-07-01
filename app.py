# app.py
from flask import Flask, request
import telegram
import yfinance as yf
from datetime import datetime
import os

TOKEN = os.environ["BOT_TOKEN"]
bot = telegram.Bot(token=TOKEN)

app = Flask(__name__)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    handle_message(update)
    return "ok"

@app.route("/")
def home():
    return "Bot is live!"

def analyze_nifty_move(target_level, target_date_str):
    ticker = yf.Ticker("^NSEI")
    now = datetime.now()
    is_market_hours = 9 <= now.hour <= 15
    hist = ticker.history(period="10y", interval="1d").dropna()

    current_price = hist.iloc[-1]['Open'] if is_market_hours else hist.iloc[-1]['Close']
    target_price = float(target_level)
    move_needed = target_price - current_price
    direction = "up" if move_needed > 0 else "down"
    abs_move = abs(move_needed)

    target_date = datetime.strptime(target_date_str, "%d/%m/%Y")
    days = (target_date - now).days

    count = 0
    for i in range(len(hist) - days):
        start = hist.iloc[i]
        end = hist.iloc[i + days]
        start_price = start['Open'] if is_market_hours else start['Close']
        end_price = end['Close']
        if (start_price - end_price >= abs_move and direction == "down") or \
           (end_price - start_price >= abs_move and direction == "up"):
            count += 1

    return f"NIFTY needs to move {direction} by {abs_move:.2f} in {days} days.\n" \
           f"Such a move has happened {count} times in the last 10 years."

def handle_message(update):
    message = update.message
    text = message.text
    try:
        symbol, target_level, target_date = [x.strip() for x in text.split(",")]
        if symbol.upper() != "NIFTY":
            message.reply_text("Only NIFTY is supported right now.")
            return
        result = analyze_nifty_move(target_level, target_date)
        message.reply_text(result)
    except Exception as e:
        message.reply_text("Invalid input. Use format: NIFTY, 25000, 03/07/2025")
