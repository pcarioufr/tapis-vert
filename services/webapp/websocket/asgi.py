from ddtrace import tracer
from ddtrace.contrib.asyncio import context_provider
tracer.configure(context_provider=context_provider)

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from managers import WebSocketManager

import utils
log = utils.get_logger(__name__)

app = FastAPI()

# Adding the CORS middleware to the app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

socket_manager = WebSocketManager()

@app.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str):
    
    await socket_manager.add_user_to_room(room_id, user_id, websocket)

    try:

        while True:

            data = await websocket.receive_text()
            with tracer.trace("receive"):
                message = f"user::{user_id}:{data}"
                await socket_manager.broadcast_to_room(room_id, message)

    except WebSocketDisconnect:

        await socket_manager.remove_user_from_room(room_id, user_id, websocket)


