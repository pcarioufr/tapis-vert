import asyncio
import redis.asyncio as aioredis
import os
from fastapi import WebSocket

from models import User

import utils
log = utils.get_logger(__name__)


class RedisPubSubManager:
    """
        Initializes the RedisPubSubManager.

    Args:
        host (str): Redis server host.
        port (int): Redis server port.
    """

    def __init__(self):
        self.redis_host = os.environ.get("REDIS_HOST")
        self.redis_port = 6379
        self.redis_db   = os.environ.get("REDIS_PUBSUB_DB")
        self.pubsub = None

    async def _get_redis_connection(self) -> aioredis.Redis:
        """
        Establishes a connection to Redis.

        Returns:
            aioredis.Redis: Redis connection object.
        """
        return aioredis.Redis(host=self.redis_host,
                              port=self.redis_port,
                              db=self.redis_db,
                              auto_close_connection_pool=False)

    async def connect(self) -> None:
        """
        Connects to the Redis server and initializes the pubsub client.
        """
        self.redis_connection = await self._get_redis_connection()
        self.pubsub = self.redis_connection.pubsub()

    async def _publish(self, room_id: str, message: str) -> None:
        """
        Publishes a message to a specific Redis channel.

        Args:
            room_id (str): Channel or room ID.
            message (str): Message to be published.
        """
        await self.redis_connection.publish(room_id, message)

    async def subscribe(self, room_id: str) -> aioredis.Redis:
        """
        Subscribes to a Redis channel.

        Args:
            room_id (str): Channel or room ID to subscribe to.

        Returns:
            aioredis.ChannelSubscribe: PubSub object for the subscribed channel.
        """
        await self.pubsub.subscribe(room_id)
        return self.pubsub

    async def unsubscribe(self, room_id: str) -> None:
        """
        Unsubscribes from a Redis channel.

        Args:
            room_id (str): Channel or room ID to unsubscribe from.
        """
        await self.pubsub.unsubscribe(room_id)


class WebSocketManager:

    def __init__(self):
        """
        Initializes the WebSocketManager.

        Attributes:
            rooms (dict): A dictionary to store WebSocket connections in different rooms.
            pubsub_client (RedisPubSubManager): An instance of the RedisPubSubManager class for pub-sub functionality.
        """
        self.rooms: dict = {}
        self.pubsub_client = RedisPubSubManager()

    async def add_user_to_room(self, room_id: str, user_id: str, websocket: WebSocket) -> None:
        """
        Adds a user's WebSocket connection to a room.

        Args:
            room_id (str): Room ID or channel name.
            user_id (str): User ID of the user owning the websocket.
            websocket (WebSocket): WebSocket connection object.
        """
        await websocket.accept()

        if room_id in self.rooms:
            self.rooms[room_id].append(websocket)
        else:
            self.rooms[room_id] = [websocket]

            await self.pubsub_client.connect()
            pubsub_subscriber = await self.pubsub_client.subscribe(room_id)

            # Create an event to signal when the pubsub reader is ready
            ready_event = asyncio.Event()
            asyncio.create_task(self._pubsub_data_reader(pubsub_subscriber, ready_event))

            # Wait until the pubsub reader signals that it's ready
            await ready_event.wait()

        try:
            User.get_by_id(user_id).rooms().set(room_id, status="online")
            utils.publish(room_id, "user:online", user_id)

        except Exception as e:
            log.debug(f"Exception: {e}")
            pass # legit exception for visitors
        finally:
            log.info(f"user {user_id} joined room {room_id}")


    async def broadcast_to_room(self, room_id: str, message: str) -> None:
        """
        Broadcasts a message to all connected WebSockets in a room.

        Args:
            room_id (str): Room ID or channel name.
            message (str): Message to be broadcasted.
        """
        await self.pubsub_client._publish(room_id, message)

    async def remove_user_from_room(self, room_id: str, user_id: str, websocket: WebSocket) -> None:
        """
        Removes a user's WebSocket connection from a room.

        Args:
            room_id (str): Room ID or channel name.
            user_id (str): User ID of the user owning the websocket.
            websocket (WebSocket): WebSocket connection object.
        """
        self.rooms[room_id].remove(websocket)

        if len(self.rooms[room_id]) == 0:
            del self.rooms[room_id]
            await self.pubsub_client.unsubscribe(room_id)


        try:
            User.get_by_id(user_id).rooms().set(room_id, status="offline")
            utils.publish(room_id, "user:offline", user_id)
        except Exception as e:
            log.debug(f"Exception: {e}")
            pass # legit exception for visitors
        finally:
            log.info(f"user {user_id} left room {room_id}")


    async def _pubsub_data_reader(self, pubsub_subscriber, ready_event=None):
        """
        Reads and broadcasts messages received from Redis PubSub.

        Args:
            pubsub_subscriber (aioredis.ChannelSubscribe): PubSub object for the subscribed channel.
            ready_event (asyncio.Event): Optional event to signal when the reader is ready.

        """
        if ready_event:
            ready_event.set()  # Signal that the reader is ready
            
        while True:
            message = await pubsub_subscriber.get_message(ignore_subscribe_messages=True)
            if message is not None:

                room_id = message['channel'].decode('utf-8')
                all_sockets = self.rooms[room_id]
                for socket in all_sockets:

                    data = message['data'].decode('utf-8')
                    log.info(data)
                    await socket.send_text(data)
