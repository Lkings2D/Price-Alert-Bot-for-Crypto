import os
import threading
import requests
import time
from fastapi import FastAPI, Header, HTTPException
from contextlib import asynccontextmanager

# ---------------- ENV ---------------- #

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
API_KEY = os.getenv("API_KEY")

alerts = {}

# ---------------- FASTAPI ---------------- #

app = FastAPI()

# ---------------- SECURITY ---------------- #

def verify_key(x_api_key: str):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

# ---------------- DISCORD ---------------- #

def send_alert(msg):
    try:
        if DISCORD_WEBHOOK:
            requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=5)
    except Exception as e:
        print("DISCORD ERROR:", e)

# ---------------- PRICE LOOP ---------------- #

def price_loop():
    print("🔥 PRICE LOOP STARTED")

    url = "https://api.binance.com/api/v3/ticker/price"

    while True:
        try:
            response = requests.get(url, timeout=10)

            # SAFE JSON PARSE
            try:
                res = response.json()
            except Exception as e:
                print("BAD JSON:", response.text)
                time.sleep(5)
                continue

            # 🔥 FIX: normalize Binance response
            if isinstance(res, dict):
                res = [res]

            if not isinstance(res, list):
                print("BAD RESPONSE TYPE:", type(res))
                time.sleep(5)
                continue

            for item in res:
                # strict safety
                if not isinstance(item, dict):
                    continue

                symbol = item.get("symbol")
                price = item.get("price")

                if not symbol or not price:
                    continue

                try:
                    price = float(price)
                except:
                    continue

                # ALERT LOGIC
                if symbol in alerts:
                    for target in alerts[symbol][:]:
                        if price >= target:
                            print("🔔 TRIGGER", symbol, price)
                            send_alert(f"🔔 {symbol} hit {price}")
                            alerts[symbol].remove(target)

            time.sleep(2)

        except Exception as e:
            print("LOOP ERROR:", e)
            time.sleep(5)

# ---------------- STARTUP (RAILWAY SAFE) ---------------- #

def start_loop():
    price_loop()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 FASTAPI STARTED")

    thread = threading.Thread(target=start_loop, daemon=True)
    thread.start()

    yield

app = FastAPI(lifespan=lifespan)

# ---------------- HEALTH CHECK ---------------- #

@app.get("/")
def root():
    return {"status": "alive"}

# ---------------- API ---------------- #

@app.get("/alerts")
def get_alerts():
    return alerts


@app.post("/add")
def add_alert(data: dict, x_api_key: str = Header(None)):
    verify_key(x_api_key)

    coin = data["coin"].upper()
    price = float(data["price"])

    alerts.setdefault(coin, []).append(price)

    print("➕ ADDED", coin, price)

    return {"status": "added", "alerts": alerts}


@app.post("/remove")
def remove_alert(data: dict, x_api_key: str = Header(None)):
    verify_key(x_api_key)

    coin = data["coin"].upper()
    price = float(data["price"])

    if coin in alerts and price in alerts[coin]:
        alerts[coin].remove(price)

    print("➖ REMOVED", coin, price)

    return {"status": "removed", "alerts": alerts}