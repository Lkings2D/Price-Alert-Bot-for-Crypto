import os
import requests
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
    except:
        pass

# ---------------- HEALTH ---------------- #

@app.get("/")
def root():
    return {"status": "alive"}

# ---------------- ALERTS API ---------------- #

@app.get("/alerts")
def get_alerts():
    return alerts


@app.post("/add")
def add_alert(data: dict, x_api_key: str = Header(None)):
    verify_key(x_api_key)

    coin = data["coin"].upper()
    price = float(data["price"])

    alerts.setdefault(coin, []).append(price)

    return {"status": "added", "alerts": alerts}


@app.post("/remove")
def remove_alert(data: dict, x_api_key: str = Header(None)):
    verify_key(x_api_key)

    coin = data["coin"].upper()
    price = float(data["price"])

    if coin in alerts and price in alerts[coin]:
        alerts[coin].remove(price)

    return {"status": "removed"}