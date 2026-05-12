from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import asyncio
import websockets
import json
import requests
import os

app = FastAPI()

templates = Jinja2Templates(directory="templates")

alerts = []

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
PASSWORD = os.getenv("DASH_PASSWORD")

SUPPORTED_COINS = ["BTC", "ETH", "LINK", "SOL", "XRP", "XMR"]

# LOGIN + DASHBOARD
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, password: str = ""):

    if password != PASSWORD:

        return HTMLResponse("""

        <html>

        <body style="font-family:sans-serif;padding:40px;">

            <h1>Crypto Alert Login</h1>

            <form>

                <input
                    type="password"
                    name="password"
                    placeholder="Password"
                >

                <button type="submit">
                    Enter
                </button>

            </form>

        </body>

        </html>

        """)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "alerts": alerts,
            "password": password,
            "coins": SUPPORTED_COINS
        }
    )

# ADD ALERT
@app.post("/add")
async def add_alert(
    request: Request,
    password: str = Form(...),
    coin: str = Form(...),
    price: float = Form(...)
):

    if password != PASSWORD:
        return {"error": "wrong password"}

    coin = coin.upper()
    if coin not in SUPPORTED_COINS:
        return {"error": "unsupported coin"}

    alerts.append({"coin": coin, "price": price})

    return HTMLResponse(f"""

    <script>
        window.location.href='/?password={password}'
    </script>

    """)

# REMOVE ALERT
@app.post("/remove")
async def remove_alert(
    request: Request,
    password: str = Form(...),
    index: int = Form(...)
):

    if password != PASSWORD:
        return {"error": "wrong password"}

    if 0 <= index < len(alerts):
        alerts.pop(index)

    return HTMLResponse(f"""

    <script>
        window.location.href='/?password={password}'
    </script>

    """)

# REALTIME BINANCE SOCKET FOR A SINGLE COIN
async def socket_loop(coin: str):

    symbol = f"{coin.lower()}usdt"
    uri = f"wss://stream.binance.com:9443/ws/{symbol}@trade"

    async with websockets.connect(uri) as ws:

        while True:

            data = json.loads(await ws.recv())

            current = float(data["p"])

            triggered = []

            for alert in alerts:
                if alert["coin"] == coin and current >= alert["price"]:
                    requests.post(
                        WEBHOOK,
                        json={
                            "content": f"🚨 {coin} hit ${alert['price']:,.2f} (now ${current:,.2f})"
                        }
                    )
                    triggered.append(alert)

            for t in triggered:
                if t in alerts:
                    alerts.remove(t)

async def socket_loop_with_retry(coin: str):

    while True:

        try:
            await socket_loop(coin)
        except Exception as e:
            print(f"[{coin}] Socket error: {e}. Retrying in 30 seconds...")
            await asyncio.sleep(30)

# START SOCKETS FOR ALL COINS
@app.on_event("startup")
async def startup():

    for coin in SUPPORTED_COINS:
        asyncio.create_task(socket_loop_with_retry(coin))
