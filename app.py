from flask import Flask, request
import telegram
import yfinance as yf
import matplotlib.pyplot as plt
import io
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

def generate_yearly_occurrence_chart(hist, abs_pct_move, direction, days, is_market_hours):
    year_counts = {}

    for i in range(len(hist) - days):
        start = hist.iloc[i]
        end = hist.iloc[i + days]
        start_price = start['Open'] if is_market_hours else start['Close']
        end_price = end['Close']
        pct_change = ((end_price - start_price) / start_price) * 100

        condition = (
            direction == "up" and pct_change >= abs_pct_move
        ) or (
            direction == "down" and pct_change <= -abs_pct_move
        )

        if condition:
            year = end.name.year
            year_counts[year] = year_counts.get(year, 0) + 1

    years = sorted(year_counts.keys())
    counts = [year_counts[year] for year in years]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(years, counts)
    ax.set_title("Occurrences per Year")
    ax.set_xlabel("Year")
    ax.set_ylabel("Count")
    plt.tight_layout()

    img_bytes = io.BytesIO()
    plt.savefig(img_bytes, format='png')
    img_bytes.seek(0)
    plt.close()
    return img_bytes

def analyze_nifty_move(target_level, date_or_days_str):
    ticker = yf.Ticker("^NSEI")
    now = datetime.now()
    is_market_hours = 9 <= now.hour <= 15
    hist = ticker.history(period="10y", interval="1d").dropna()

    current_price = hist.iloc[-1]['Open'] if is_market_hours else hist.iloc[-1]['Close']
    target_price = float(target_level)
    pct_move_needed = ((target_price - current_price) / current_price) * 100
    direction = "up" if pct_move_needed > 0 else "down"
    abs_pct_move = abs(pct_move_needed)

    try:
        days = int(date_or_days_str)
    except ValueError:
        target_date = datetime.strptime(date_or_days_str, "%d/%m/%Y")
        days = (target_date - now).days

    if days <= 0:
        return None, None, "Target date must be in the future or a positive number of days."

    count = 0
    total_windows = len(hist) - days

    for i in range(total_windows):
        start = hist.iloc[i]
        end = hist.iloc[i + days]
        start_price = start['Open'] if is_market_hours else start['Close']
        end_price = end['Close']
        pct_change = ((end_price - start_price) / start_price) * 100

        if direction == "up" and pct_change >= abs_pct_move:
            count += 1
        elif direction == "down" and pct_change <= -abs_pct_move:
            count += 1

    probability = (count / total_windows) * 100

    text = (
        f"NIFTY Move Analysis\n"
        f"----------------------\n"
        f"Current Price: {current_price:.2f}\n"
        f"Target Price: {target_price:.2f}\n"
        f"Required Move: {direction} by {target_price - current_price:.2f} points "
        f"({abs_pct_move:.2f}%)\n"
        f"Time Horizon: {days} days\n\n"
        f"Historical Matches: {count} times\n"
        f"Lookback Comparisons: {total_windows} cases\n"
        f"Estimated Probability: {probability:.2f}%"
    )

    img = generate_yearly_occurrence_chart(hist, abs_pct_move, direction, days, is_market_hours)
    return text, img, None

def handle_message(update):
    message = update.message
    text = message.text.strip()
    try:
        symbol, target_level, date_or_days = [x.strip() for x in text.split(",")]
        if symbol.upper() != "NIFTY":
            message.reply_text("Only NIFTY is supported right now.")
            return

        result_text, chart_image, error = analyze_nifty_move(target_level, date_or_days)
        if error:
            message.reply_text(error)
        else:
            message.reply_text(result_text)
            message.reply_photo(chart_image)
    except Exception as e:
        message.reply_text(
            "Invalid input. Use format:\n"
            "NIFTY, 25000, 03/07/2025\n"
            "or\n"
            "NIFTY, 25000, 3"
        )
