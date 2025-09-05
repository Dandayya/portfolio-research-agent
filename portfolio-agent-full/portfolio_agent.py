import os
import json
import requests
import yfinance as yf
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PORTFOLIO_FILE = "portfolio.json"

def fetch_stock_price(symbol):
    try:
        t = yf.Ticker(symbol)
        data = t.history(period="2d")
        if not data.empty and len(data) >= 2:
            last_close = float(data['Close'][-1])
            prev_close = float(data['Close'][-2])
            return last_close, prev_close
        elif not data.empty:
            last_close = float(data['Close'][-1])
            return last_close, None
        return None, None
    except:
        return None, None

def fetch_nifty_index():
    try:
        t = yf.Ticker("^NSEI")
        data = t.history(period="2d")
        if not data.empty and len(data) >= 2:
            last = float(data['Close'][-1])
            prev = float(data['Close'][-2])
            change = last - prev
            pct = (change / prev * 100) if prev else 0
            return last, change, pct
        return None, None, None
    except:
        return None, None, None

def compute_message(portfolio):
    lines = []
    nifty, change, pct = fetch_nifty_index()

    header = f"📊 Portfolio Update — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    if nifty:
        header += f"\nNIFTY: {nifty:.2f} ({change:+.2f}, {pct:+.2f}%)"
    lines.append(header + "\n")

    total_value = 0
    total_cost = 0

    gainer = None
    loser = None

    for s in portfolio["stocks"]:
        sym, qty, avg = s["symbol"], s["qty"], s["avg_price"]
        price, prev = fetch_stock_price(sym)
        if price is None:
            lines.append(f"{sym}: fetch failed")
            continue
        value, cost = price * qty, avg * qty
        pnl = value - cost
        pnl_pct = (pnl / cost * 100) if cost else 0
        total_value += value
        total_cost += cost
        line = f"{sym} • Qty {qty} • LTP {price:.2f} • P&L {pnl:+.2f} ({pnl_pct:+.2f}%)"
        lines.append(line)

        # Track gainer/loser
        if gainer is None or pnl_pct > gainer[1]:
            gainer = (sym, pnl_pct)
        if loser is None or pnl_pct < loser[1]:
            loser = (sym, pnl_pct)

    overall_pnl = total_value - total_cost
    overall_pct = (overall_pnl / total_cost * 100) if total_cost else 0
    lines.append("\n— Summary —")
    lines.append(f"Total Value: {total_value:.2f}")
    lines.append(f"Total Cost: {total_cost:.2f}")
    lines.append(f"Overall P&L: {overall_pnl:+.2f} ({overall_pct:+.2f}%)")

    if gainer and loser:
        lines.append("\n— Highlights —")
        lines.append(f"🏆 Top Gainer: {gainer[0]} ({gainer[1]:+.2f}%)")
        lines.append(f"📉 Top Loser: {loser[0]} ({loser[1]:+.2f}%)")

    return "\n".join(lines)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text})

def main():
    with open(PORTFOLIO_FILE, "r") as f:
        portfolio = json.load(f)
    message = compute_message(portfolio)
    send_telegram_message(message)

if __name__ == "__main__":
    main()
