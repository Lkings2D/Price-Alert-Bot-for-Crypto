import os
import threading
import requests
import time
from fastapi import FastAPI, Header, HTTPException

# ---------------- ENV ---------------- #

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
API_KEY = os.getenv("API_KEY")

PORT = int(os.environ.get("PORT", 8080))

# ---------------- STATE ---------------- #

alerts = {}

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

            try:
                res = response.json()
            except Exception:
                print("❌ JSON PARSE FAILED:", response.text)
                time.sleep(5)
                continue

            if isinstance(res, dict):
                res = [res]

            if not isinstance(res, list):
                print("❌ BAD RESPONSE TYPE:", type(res))
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

                # debug only LINKUSDT
                if symbol == "LINKUSDT":
                    print("FOUND LINK:", price)

                if symbol in alerts and alerts[symbol]:
                    for target in alerts[symbol][:]:
                        print("CHECK", symbol, price, target)

                        if price >= target:
                            print("🔔 TRIGGER", symbol, price)
                            send_alert(f"🔔 {symbol} hit {price}")
                            alerts[symbol].remove(target)

            time.sleep(2)

        except Exception as e:
            print("❌ LOOP ERROR:", e)
            time.sleep(5)

# ---------------- FASTAPI ---------------- #

app = FastAPI()

@app.on_event("startup")
def startup():
    print("🚀 FASTAPI STARTUP")

    thread = threading.Thread(target=price_loop, daemon=True)
    thread.start()

# ---------------- ROUTES ---------------- #

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

# ---------------- RAILWAY ENTRYPOINT ---------------- #

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)