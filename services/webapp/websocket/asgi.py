from models import User

from ddtrace import tracer
from ddtrace.contrib.asyncio import context_provider
tracer.configure(context_provider=context_provider)

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from managers import WebSocketManager


from utils import get_logger
log = get_logger(__name__)

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

    
    await socket_manager.add_user_to_room(room_id, websocket)

    log.info(f"websocket opened for user {user_id} in room {room_id}")

    try:
        User.get(user_id).status = "online"
        log.info(f"user {user_id} online")
    except:
        # visitor
        pass

    try:
        while True:

            data = await websocket.receive_text()

            with tracer.trace("receive"):

                message = f"user::{user_id}:{data}"
                await socket_manager.broadcast_to_room(room_id, message)

    except WebSocketDisconnect:

        await socket_manager.remove_user_from_room(room_id, websocket)

        try:
            User.get(user_id).status = "offline"
            log.info(f"user {user_id} offline")
        except:
            # visitor
            pass
