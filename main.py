import os
import requests
from fastapi import FastAPI

print("🟢 FILE STARTING")

app = FastAPI()

print("🟢 FASTAPI CREATED")

@app.get("/")
def root():
    print("📡 ROOT HIT")
    return {"status": "alive"}