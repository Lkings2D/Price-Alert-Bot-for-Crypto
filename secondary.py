# secondary.py
# Temporary script to fetch and display popular stock prices using yfinance

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import asyncio
import yfinance as yf
import os

app = FastAPI()

templates = Jinja2Templates(directory="templates")

alerts = []
previous_prices = {}

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
PASSWORD = os.getenv("DASH_PASSWORD")
UUID = os.getenv("SECRET_UUID")

# If you know the correct ticker (e.g., for a European exchange), replace below. Otherwise, use popular stocks as examples:
SUPPORTED_STOCKS = ["RKLB","INTU","NBIS"]

@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, password: str = ""):
    if password != PASSWORD:
        return HTMLResponse("""
        <html>
        <body style="font-family:sans-serif;padding:40px;">
            <h1>Stock Alert Login</h1>
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
            "stocks": SUPPORTED_STOCKS
        }
    )

@app.post("/add")
async def add_alert(
    request: Request,
    password: str = Form(...),
    stock: str = Form(...),
    price: float = Form(...),
    direction: str = Form("down")
):
    if password != PASSWORD:
        return {"error": "wrong password"}
    stock = stock.upper()
    if stock not in SUPPORTED_STOCKS:
        return {"error": "unsupported stock"}
    if direction not in ("down", "up"):
        direction = "down"
    alerts.append({"stock": stock, "price": price, "direction": direction})
    return HTMLResponse(f"""
    <script>
        window.location.href='/?password={password}'
    </script>
    """)

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

async def price_loop():
    while True:
        try:
            prices = {}
            for stock in SUPPORTED_STOCKS:
                ticker = yf.Ticker(stock)
                # Fetch 1-minute interval data for today
                data = ticker.history(period="1d", interval="1m")
                if not data.empty:
                    # Use the most recent close price
                    prices[stock] = float(data['Close'].iloc[-1])
                else:
                    print(f"No intraday data found for {stock}")
            print("Prices:", prices)
            triggered = []
            for alert in alerts:
                stock = alert["stock"]
                current = prices.get(stock)
                alert_price = alert["price"]
                direction = alert.get("direction", "down")
                prev = previous_prices.get(stock)
                crossed = False
                if prev is not None and current is not None:
                    if direction == "down":
                        if prev > alert_price and current <= alert_price:
                            crossed = True
                    elif direction == "up":
                        if prev < alert_price and current >= alert_price:
                            crossed = True
                if crossed:
                    msg = f"<@{UUID}> {stock} hit ${alert_price:,} (now ${current:,})"
                    if WEBHOOK:
                        import requests
                        requests.post(
                            WEBHOOK,
                            json={"content": msg}
                        )
                    triggered.append(alert)
            for stock in SUPPORTED_STOCKS:
                price = prices.get(stock)
                if price is not None:
                    previous_prices[stock] = price
            for t in triggered:
                if t in alerts:
                    alerts.remove(t)
        except Exception as e:
            import traceback
            print(f"Price fetch error: {e}")
            traceback.print_exc()
        await asyncio.sleep(10)

@app.on_event("startup")
async def startup():
    asyncio.create_task(price_loop())
