import os
import json
import time
import smtplib
import requests
from email.mime.text import MIMEText
from datetime import datetime

THRESHOLD = 10
VS_CURRENCY = "usd"
COOLDOWN_MINUTES = 120
STATE_FILE = "state.json"

EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_TO = os.environ["EMAIL_TO"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]

URL = "https://api.coingecko.com/api/v3/coins/markets"

def fetch():
    coins = []
    for page, per_page in [(1, 250), (2, 50)]:
        params = {
            "vs_currency": VS_CURRENCY,
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": page,
            "price_change_percentage": "1h",
        }
        r = requests.get(URL, params=params, timeout=30)
        r.raise_for_status()
        coins.extend(r.json())
    return coins

def send_email(body):
    msg = MIMEText(body)
    msg["Subject"] = "🚨 Crypto Alert: +10% in 1h"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.starttls()
        s.login(EMAIL_FROM, EMAIL_PASSWORD)
        s.send_message(msg)

def main():
    state = json.load(open(STATE_FILE)) if os.path.exists(STATE_FILE) else {}
    now = time.time()
    hits = []

    for c in fetch():
        ch = c.get("price_change_percentage_1h_in_currency")
        if ch and ch >= THRESHOLD:
            last = state.get(c["id"], 0)
            if now - last > COOLDOWN_MINUTES * 60:
                hits.append((c["name"], c["symbol"], ch))
                state[c["id"]] = now

    if hits:
        hits.sort(key=lambda x: x[2], reverse=True)
        body = f"{datetime.utcnow()} UTC\n\n"
        body += "\n".join(
            f"{n} ({s.upper()}): {c:.2f}%"
            for n, s, c in hits
        )
        send_email(body)
        json.dump(state, open(STATE_FILE, "w"))

if __name__ == "__main__":
    main()
