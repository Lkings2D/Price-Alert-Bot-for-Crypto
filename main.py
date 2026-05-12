import os
from fastapi import FastAPI

print("🟢 STARTING APP")

app = FastAPI()

@app.get("/")
def root():
    return {"status": "alive", "ready": True}