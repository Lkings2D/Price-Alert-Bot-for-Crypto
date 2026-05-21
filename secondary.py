from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import asyncio
from datetime import datetime, time, timedelta
import requests
import os
from zoneinfo import ZoneInfo
from typing import Optional

app = FastAPI()

# Holiday handling: prefer the `holidays` package for accurate US market holidays.
try:
    import holidays as _holidays  # type: ignore
    _HOLIDAYS_LIB = True
    _US_HOLIDAYS = _holidays.UnitedStates()
except Exception:
    _HOLIDAYS_LIB = False
    _US_HOLIDAYS = None

# Allow skipping holiday checks via env for testing
SKIP_HOLIDAYS = os.getenv("SKIP_HOLIDAYS", "").lower() in ("1", "true", "yes")

templates = Jinja2Templates(directory="templates")

stock_alerts = []

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
PASSWORD = os.getenv("DASH_PASSWORD")
UUID = os.getenv("SECRET_UUID")

SUPPORTED_STOCKS = ["RKLB", "INTU", "NBIS"]

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
EASTERN = ZoneInfo("America/New_York")
MARKET_OPEN = time(10, 30)
MARKET_CLOSE = time(17, 0)


def market_is_open(now: Optional[datetime] = None) -> bool:
    current_time = now or datetime.now(EASTERN)
    current_time = current_time.astimezone(EASTERN)
    # Closed on US market holidays (if the `holidays` package is available)
    if not SKIP_HOLIDAYS and _HOLIDAYS_LIB and _US_HOLIDAYS is not None:
        if current_time.date() in _US_HOLIDAYS:
            return False
    return MARKET_OPEN <= current_time.time() < MARKET_CLOSE


def seconds_until_market_open(now: Optional[datetime] = None) -> float:
    current_time = now or datetime.now(EASTERN)
    current_time = current_time.astimezone(EASTERN)

    def build_open(day: datetime) -> datetime:
        return day.replace(
            hour=MARKET_OPEN.hour,
            minute=MARKET_OPEN.minute,
            second=0,
            microsecond=0,
        )

    today_open = build_open(current_time)
    # If today is a business day and before today's open, and today is not a holiday,
    # return seconds until today's open.
    is_today_holiday = False
    if not SKIP_HOLIDAYS and _HOLIDAYS_LIB and _US_HOLIDAYS is not None:
        is_today_holiday = current_time.date() in _US_HOLIDAYS

    if current_time < today_open and current_time.weekday() < 5 and not is_today_holiday:
        return (today_open - current_time).total_seconds()

    # Otherwise find the next weekday that is not a holiday
    next_day = current_time + timedelta(days=1)
    while next_day.weekday() >= 5 or (not SKIP_HOLIDAYS and _HOLIDAYS_LIB and _US_HOLIDAYS is not None and next_day.date() in _US_HOLIDAYS):
        next_day += timedelta(days=1)
    next_open = build_open(next_day)
    return (next_open - current_time).total_seconds()


def get_live_stock_price(stock: str):
    response = requests.get(
        YAHOO_CHART_URL.format(symbol=stock),
        params={"range": "1d", "interval": "1m", "includePrePost": "true"},
        timeout=10,
        headers={"User-Agent": "Mozilla/5.0"},
    )

    if response.status_code != 200:
        print(f"Yahoo chart request failed for {stock}: {response.status_code}")
        return None

    payload = response.json()
    chart = payload.get("chart", {})
    result = chart.get("result", [])
    if not result:
        return None

    meta = result[0].get("meta", {})
    for field in ("postMarketPrice", "preMarketPrice", "regularMarketPrice", "currentPrice"):
        value = meta.get(field)
        if value is not None:
            return float(value)

    indicators = result[0].get("indicators", {}).get("quote", [])
    timestamps = result[0].get("timestamp", [])
    if indicators and timestamps:
        closes = indicators[0].get("close", [])
        for close_price in reversed(closes):
            if close_price is not None:
                return float(close_price)

    return None

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
            "stock_alerts": stock_alerts,
            "password": password,
            "stocks": SUPPORTED_STOCKS,
            "mode": "stocks"
        }
    )

@app.post("/add")
async def add_alert(
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

    stock_alerts.append({"stock": stock, "price": price, "direction": direction})

    return HTMLResponse(f"""
    <script>
        window.location.href='/?password={password}'
    </script>
    """)

@app.post("/remove")
async def remove_alert(
    password: str = Form(...),
    index: int = Form(...)
):
    if password != PASSWORD:
        return {"error": "wrong password"}

    if 0 <= index < len(stock_alerts):
        stock_alerts.pop(index)

    return HTMLResponse(f"""
    <script>
        window.location.href='/?password={password}'
    </script>
    """)


async def price_loop():
    while True:
        try:
            if not market_is_open():
                now = datetime.now(EASTERN)
                sleep_for = seconds_until_market_open(now)
                print(
                    f"Market closed in Eastern time ({now:%Y-%m-%d %H:%M:%S %Z}); "
                    f"sleeping for {sleep_for:.0f} seconds"
                )
                await asyncio.sleep(sleep_for)
                continue

            prices = {}
            for stock in SUPPORTED_STOCKS:
                price = get_live_stock_price(stock)
                if price is not None:
                    prices[stock] = price
                else:
                    print(f"No live quote found for {stock}")
            print("Prices:", prices)

            triggered = []
            for alert in stock_alerts:
                stock = alert.get("stock")
                if not stock:
                    continue
                current = prices.get(stock)
                alert_price = alert["price"]
                direction = alert.get("direction", "down")
                crossed = False
                if current is not None:
                    if direction == "down":
                        crossed = current <= alert_price
                    elif direction == "up":
                        crossed = current >= alert_price
                if crossed:
                    msg = f"<@{UUID}> {stock} hit ${alert_price:,} (now ${current:,})"
                    if WEBHOOK:
                        try:
                            requests.post(
                                WEBHOOK,
                                json={"content": msg},
                                timeout=10,
                            )
                        except Exception as webhook_error:
                            print(f"Discord webhook error: {webhook_error}")
                    triggered.append(alert)

            for t in triggered:
                if t in stock_alerts:
                    stock_alerts.remove(t)

        except Exception as e:
            import traceback
            print(f"Price fetch error: {e}")
            traceback.print_exc()

        await asyncio.sleep(10)

@app.on_event("startup")
async def startup():
    asyncio.create_task(price_loop())
