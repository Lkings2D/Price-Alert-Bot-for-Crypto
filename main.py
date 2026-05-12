import os
import requests
import asyncio
from fastapi import FastAPI, Header, HTTPException

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
API_KEY = os.getenv("API_KEY")

alerts = {}

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

async def price_loop():
    print("🔥 PRICE LOOP STARTED")

    url = "https://api.binance.com/api/v3/ticker/price"

    while True:
        try:
            res = requests.get(url, timeout=10).json()

            if isinstance(res, dict):
                res = [res]

            if not isinstance(res, list):
                continue

            for item in res:
                if not isinstance(item, dict):
                    continue

                symbol = item.get("symbol")
                price = item.get("price")

                # 🔥 FIX: prevent NoneType crash
                if symbol is None or price is None:
                    continue

                try:
                    price = float(price)
                except (TypeError, ValueError):
                    continue

                if symbol in alerts:
                    for target in alerts[symbol][:]:
                        try:
                            if price >= target:
                                print("🔔 TRIGGER", symbol, price)
                                send_alert(f"🔔 {symbol} hit {price}")
                                alerts[symbol].remove(target)
                        except Exception as e:
                            print("TRIGGER ERROR:", e)

            await asyncio.sleep(2)

        except Exception as e:
            print("LOOP ERROR:", e)
            await asyncio.sleep(5)

# ---------------- STARTUP ---------------- #

@app.on_event("startup")
async def startup():
    asyncio.create_task(price_loop())
    print("🚀 FASTAPI STARTED")

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

    return {"status": "added"}


@app.post("/remove")
def remove_alert(data: dict, x_api_key: str = Header(None)):
    verify_key(x_api_key)

    coin = data["coin"].upper()
    price = float(data["price"])

    if coin in alerts and price in alerts[coin]:
        alerts[coin].remove(price)

    return {"status": "removed"}