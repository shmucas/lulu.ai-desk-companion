"""
Lulu backend — FastAPI server for ESP32-S3 desk companion.

WebSocket /ws  — audio streaming + state control for the XIAO ESP32-S3
GET     /health — liveness check
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
import stt
import ollama_client
from ws_session import WSSession


@asynccontextmanager
async def lifespan(app: FastAPI):
    stt.load()
    ollama_client.warmup()
    yield


app = FastAPI(title="Lulu", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    session = WSSession(websocket)
    await session.handle()
