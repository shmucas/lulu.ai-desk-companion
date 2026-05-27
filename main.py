from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import core.agent as agent
import core.ollama_client as ollama_client
from core.schemas import ConversationResponse

_connections: set[WebSocket] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm both models so first user request isn't slow
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, ollama_client.warmup)
    yield


app = FastAPI(lifespan=lifespan)


async def _broadcast(data: dict) -> None:
    for ws in list(_connections):
        try:
            await ws.send_json(data)
        except Exception:
            _connections.discard(ws)


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@app.post("/chat", response_model=ConversationResponse)
async def chat(req: ChatRequest):
    await _broadcast({"type": "status", "value": "thinking"})
    response = await agent.run(req.message, req.history)
    await _broadcast({"type": "status", "value": "idle"})
    return response


@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws.accept()
    _connections.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        _connections.discard(ws)


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})


# Static files (placeholder index.html for later phases)
import os
_static = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static):
    app.mount("/", StaticFiles(directory=_static, html=True), name="static")
