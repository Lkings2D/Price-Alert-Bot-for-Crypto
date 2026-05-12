import os
import threading
import requests
import time
from fastapi import FastAPI, Header, HTTPException

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
API_KEY = os.getenv("API_KEY")

alerts = {}

app = FastAPI()

# ---------------- LOOP ---------------- #

def price_loop():
    print("🔥 PRICE LOOP STARTED")

    url = "https://api.binance.com/api/v3/ticker/price"

    while True:
        try:
            res = requests.get(url, timeout=10).json()

            for item in res:
                try:
                    symbol = item.get("symbol")
                    price = item.get("price")

                    if symbol is None or price is None:
                        continue

                    price = float(price)

                    if symbol in alerts:
                        for target in alerts[symbol][:]:
                            if price >= target:
                                print("🔔 TRIGGER", symbol, price)
                                if DISCORD_WEBHOOK:
                                    requests.post(DISCORD_WEBHOOK, json={"content": f"{symbol} hit {price}"})
                                alerts[symbol].remove(target)

                except:
                    continue

            time.sleep(2)

        except Exception as e:
            print("LOOP ERROR:", e)
            time.sleep(5)

# ---------------- START THREAD IMMEDIATELY ---------------- #

threading.Thread(target=price_loop, daemon=True).start()

# ---------------- API ---------------- #

@app.get("/alerts")
def get_alerts():
    return alerts


@app.post("/add")
def add_alert(data: dict, x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401)

    coin = data["coin"].upper()
    price = float(data["price"])

    alerts.setdefault(coin, []).append(price)

    return {"status": "added", "alerts": alerts}


@app.post("/remove")
def remove_alert(data: dict, x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401)

    coin = data["coin"].upper()
    price = float(data["price"])

    if coin in alerts and price in alerts[coin]:
        alerts[coin].remove(price)

    return {"status": "removed", "alerts": alerts}