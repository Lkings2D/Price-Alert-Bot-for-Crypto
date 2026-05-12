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

# LOGIN + DASHBOARD
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, password: str = ""):

    if password != PASSWORD:

        return HTMLResponse("""

        <html>

        <body style="font-family:sans-serif;padding:40px;">

            <h1>BTC Alert Login</h1>

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
        "index.html",
        {
            "request": request,
            "alerts": alerts,
            "password": password
        }
    )

# ADD ALERT
@app.post("/add")
async def add_alert(
    request: Request,
    password: str = Form(...),
    price: float = Form(...)
):

    if password != PASSWORD:
        return {"error": "wrong password"}

    alerts.append(price)

    return HTMLResponse(f"""

    <script>
        window.location.href='/?password={password}'
    </script>

    """)

# REALTIME BINANCE SOCKET
async def socket_loop():

    uri = "wss://stream.binance.com:9443/ws/btcusdt@trade"

    async with websockets.connect(uri) as ws:

        while True:

            data = json.loads(await ws.recv())

            current = float(data["p"])

            print(current)

            triggered = []

            for target in alerts:

                if current >= target:

                    requests.post(
                        WEBHOOK,
                        json={
                            "content": f"🚨 BTC hit ${target}"
                        }
                    )

                    triggered.append(target)

            for t in triggered:
                alerts.remove(t)

# START SOCKET
@app.on_event("startup")
async def startup():

    asyncio.create_task(socket_loop_with_retry())

async def socket_loop_with_retry():

    while True:

        try:
            await socket_loop()
        except Exception as e:
            print(f"Socket error: {e}. Retrying in 30 seconds...")
            await asyncio.sleep(30)