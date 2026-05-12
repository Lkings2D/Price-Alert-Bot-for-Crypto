from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import asyncio
import requests
import os

app = FastAPI()

templates = Jinja2Templates(directory="templates")

alerts = []

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
PASSWORD = os.getenv("DASH_PASSWORD")

SUPPORTED_COINS = ["BTC", "ETH", "LINK", "SOL", "XRP", "XMR"]

COINGECKO_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "LINK": "chainlink",
    "SOL": "solana",
    "XRP": "ripple",
    "XMR": "monero"
}

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

# POLL COINGECKO PRICES
async def price_loop():

    while True:

        try:

            ids = ",".join(COINGECKO_IDS[coin] for coin in SUPPORTED_COINS)

            response = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": ids, "vs_currencies": "usd"},
                timeout=10
            )

            prices = response.json()

            print("Prices:", {coin: prices.get(COINGECKO_IDS[coin], {}).get("usd") for coin in SUPPORTED_COINS})

            triggered = []

            for alert in alerts:
                coin = alert["coin"]
                gecko_id = COINGECKO_IDS.get(coin)
                current = prices.get(gecko_id, {}).get("usd")

                if current and current >= alert["price"]:
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

        except Exception as e:
            print(f"Price fetch error: {e}")

        await asyncio.sleep(10)

# START PRICE LOOP
@app.on_event("startup")
async def startup():

    asyncio.create_task(price_loop())
