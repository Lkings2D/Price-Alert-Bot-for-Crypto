from fastapi import FastAPI

app = FastAPI()

alerts = {}

@app.get("/")
def root():
    return {"status": "alive"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/alerts")
def get_alerts():
    return alerts


@app.post("/add")
def add_alert(data: dict):
    coin = data["coin"].upper()
    price = float(data["price"])

    alerts.setdefault(coin, []).append(price)

    return {"status": "added", "alerts": alerts}


@app.post("/remove")
def remove_alert(data: dict):
    coin = data["coin"].upper()
    price = float(data["price"])

    if coin in alerts and price in alerts[coin]:
        alerts[coin].remove(price)

    return {"status": "removed", "alerts": alerts}