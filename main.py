import os
import asyncio
import json
import threading
import requests
import websockets
from fastapi import FastAPI, Header, HTTPException

app = FastAPI()

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
API_KEY = os.getenv("API_KEY")

# in-memory alerts
alerts = {}

# ---------------- SECURITY ---------------- #

def verify_key(x_api_key: str):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

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


# ---------------- PRICE ENGINE ---------------- #

def send_alert(msg):
    requests.post(DISCORD_WEBHOOK, json={"content": msg})


async def price_loop():
    url = "wss://stream.binance.com:9443/ws/!ticker@arr"

    async with websockets.connect(url) as ws:
        while True:
            msg = await ws.recv()
            data = json.loads(msg)

            for item in data:
                symbol = item["s"]
                price = float(item["c"])

                if symbol in alerts:
                    for target in alerts[symbol][:]:
                        if price >= target:
                            send_alert(f"🔔 {symbol} hit {price}")
                            alerts[symbol].remove(target)


def start_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(price_loop())


threading.Thread(target=start_loop, daemon=True).start()