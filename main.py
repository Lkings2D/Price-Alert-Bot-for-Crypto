from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import asyncio
import requests
import os

app = FastAPI()

templates = Jinja2Templates(directory="templates")


alerts = []
# Track previous prices for each coin
previous_prices = {}

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
PASSWORD = os.getenv("DASH_PASSWORD")

SUPPORTED_COINS = ["BTC", "ETH", "LINK", "SOL", "XRP", "XMR", "DOGE", "PEPE"]

MEXC_SYMBOLS = {coin: f"{coin}USDT" for coin in SUPPORTED_COINS}

@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    return {"status": "ok"}

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
    price: float = Form(...),
    direction: str = Form("down")
):

    if password != PASSWORD:
        return {"error": "wrong password"}

    coin = coin.upper()
    if coin not in SUPPORTED_COINS:
        return {"error": "unsupported coin"}

    if direction not in ("down", "up"):
        direction = "down"

    alerts.append({"coin": coin, "price": price, "direction": direction})

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

# POLL MEXC PRICES

async def price_loop():

    while True:

        try:


            symbols = list(MEXC_SYMBOLS.values())
            response = requests.get(
                "https://api.mexc.com/api/v3/ticker/price",
                params={"symbols": str(symbols).replace("'", '"').replace(" ", "")},
                timeout=10
            )

            data = response.json()
            prices = {entry["symbol"]: float(entry["price"]) for entry in data}

            print("Prices:", {coin: prices.get(MEXC_SYMBOLS[coin]) for coin in SUPPORTED_COINS})

            triggered = []

            for alert in alerts:
                coin = alert["coin"]
                symbol = MEXC_SYMBOLS.get(coin)
                current = prices.get(symbol)
                alert_price = alert["price"]
                direction = alert.get("direction", "down")

                prev = previous_prices.get(coin)
                crossed = False
                if prev is not None and current is not None:
                    if direction == "down":
                        # If previous price was above alert and now is <= alert, trigger
                        if prev > alert_price and current <= alert_price:
                            crossed = True
                    elif direction == "up":
                        # If previous price was below alert and now is >= alert, trigger
                        if prev < alert_price and current >= alert_price:
                            crossed = True

                if crossed:
                    if direction == "down":
                        msg = f"<@346060319770148864> {coin} hit ${alert_price:,} (now ${current:,})"
                    else:
                        msg = f"<@346060319770148864> {coin} hit ${alert_price:,} (now ${current:,})"
                    requests.post(
                        WEBHOOK,
                        json={"content": msg}
                    )
                    triggered.append(alert)

            # Update previous prices for all coins
            for coin in SUPPORTED_COINS:
                symbol = MEXC_SYMBOLS.get(coin)
                price = prices.get(symbol)
                if price is not None:
                    previous_prices[coin] = price

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
