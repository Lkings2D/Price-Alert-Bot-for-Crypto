import os
import threading
import requests
import time
from fastapi import FastAPI, Header, HTTPException
from contextlib import asynccontextmanager

# ---------------- ENV ---------------- #

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
API_KEY = os.getenv("API_KEY")

# ---------------- STATE ---------------- #

alerts = {}

# ---------------- SECURITY ---------------- #

def verify_key(x_api_key: str):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

# ---------------- PRICE ENGINE ---------------- #

def send_alert(msg):
    if DISCORD_WEBHOOK:
        requests.post(DISCORD_WEBHOOK, json={"content": msg})


def price_loop():
    url = "https://api.binance.com/api/v3/ticker/price"

    while True:
        try:
            res = requests.get(url, timeout=10).json()

            # ensure it's a list
            if isinstance(res, dict):
                res = [res]

            for item in res:
                symbol = item.get("symbol")
                price = item.get("price")

                if not symbol or not price:
                    continue

                price = float(price)

                if symbol in alerts and alerts[symbol]:
                    for target in alerts[symbol][:]:
                        if price >= target:
                            send_alert(f"🔔 {symbol} hit {price}")
                            alerts[symbol].remove(target)

            time.sleep(2)

        except Exception as e:
            print("Price loop error:", e)
            time.sleep(5)


def start_loop():
    price_loop()

# ---------------- FASTAPI LIFESPAN ---------------- #

@asynccontextmanager
async def lifespan(app: FastAPI):
    thread = threading.Thread(target=start_loop, daemon=True)
    thread.start()
    yield

app = FastAPI(lifespan=lifespan)

# ---------------- API ---------------- #

@app.get("/alerts")
def get_alerts():
    return alerts


@app.post("/add")
def add_alert(data: dict, x_api_key: str = Header(None)):
    verify_key(x_api_key)

    coin = data["coin"].upper()
    price = float(data["price"])

    if coin not in alerts:
        alerts[coin] = []

    alerts[coin].append(price)
    return {"status": "added", "alerts": alerts}


@app.post("/remove")
def remove_alert(data: dict, x_api_key: str = Header(None)):
    verify_key(x_api_key)

    coin = data["coin"].upper()
    price = float(data["price"])

    if coin in alerts and price in alerts[coin]:
        alerts[coin].remove(price)

    return {"status": "removed", "alerts": alerts}