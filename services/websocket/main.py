from logs import log

from ddtrace import tracer
from ddtrace.contrib.asyncio import context_provider
tracer.configure(context_provider=context_provider)

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from managers import WebSocketManager
import json

# import argparse
# parser = argparse.ArgumentParser()
# parser.add_argument("-p", "--port", default=8000, type=int)
# args = parser.parse_args()


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


# @tracer.wrap(service="websocket", resource="test")
# @app.websocket("/ws/{room_id}/{user_id}")
# async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str):

#     await websocket.accept()
#     while True:

#         with tracer.trace("step"):

#             log.info("request {}".format(websocket.headers))
#             log.info("url {}".format(websocket.url))
#             log.info("path_params {}".format(websocket.path_params))
#             log.info("query_params {}".format(websocket.query_params))

#             data = await websocket.receive_text()
#             await websocket.send_text(f"You sent: {data}")


@app.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str):

    await socket_manager.add_user_to_room(room_id, websocket)
    message = {
        "user_id": user_id,
        "room_id": room_id,
        "message": f"User {user_id} connected to room - {room_id}"
    }

    await socket_manager.broadcast_to_room(room_id, json.dumps(message))
    try:
        while True:

            data = await websocket.receive_text()
            with tracer.trace("receive"):
                message = {
                    "user_id": user_id,
                    "room_id": room_id,
                    "message": data
                }
            await socket_manager.broadcast_to_room(room_id, json.dumps(message))

    except WebSocketDisconnect:
        await socket_manager.remove_user_from_room(room_id, websocket)

        message = {
            "user_id": user_id,
            "room_id": room_id,
            "message": f"User {user_id} disconnected from room - {room_id}"
        }
        await socket_manager.broadcast_to_room(room_id, json.dumps(message))

