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

# ---------------- DISCORD ---------------- #

def send_alert(msg):
    if DISCORD_WEBHOOK:
        requests.post(DISCORD_WEBHOOK, json={"content": msg})

# ---------------- PRICE LOOP ---------------- #

def price_loop():
    print("🔥 PRICE LOOP STARTED")

    url = "https://api.binance.com/api/v3/ticker/price"

    while True:
        try:
            res = requests.get(url, timeout=10).json()

            # 🔥 FORCE SAFE TYPE
            if isinstance(res, dict):
                res = [res]

            if not isinstance(res, list):
                print("❌ Unexpected response type:", type(res), res)
                time.sleep(5)
                continue

            for item in res:
                if not isinstance(item, dict):
                    continue

                symbol = item.get("symbol")
                price = item.get("price")

                if not symbol or not price:
                    continue

                price = float(price)

                if symbol in alerts and alerts[symbol]:
                    for target in alerts[symbol][:]:
                        print(f"CHECK {symbol} {price} vs {target}")

                        if price >= target:
                            print(f"🔔 TRIGGERED {symbol} {price}")
                            send_alert(f"{symbol} hit {price}")
                            alerts[symbol].remove(target)

            time.sleep(2)

        except Exception as e:
            print("❌ LOOP ERROR:", e)
            time.sleep(5)
# ---------------- STARTUP ---------------- #

def start_loop():
    price_loop()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 FASTAPI STARTUP")
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

    print(f"➕ ADDED ALERT {coin} @ {price}")

    return {"status": "added", "alerts": alerts}


@app.post("/remove")
def remove_alert(data: dict, x_api_key: str = Header(None)):
    verify_key(x_api_key)

    coin = data["coin"].upper()
    price = float(data["price"])

    if coin in alerts and price in alerts[coin]:
        alerts[coin].remove(price)

    print(f"➖ REMOVED ALERT {coin} @ {price}")

    return {"status": "removed", "alerts": alerts}