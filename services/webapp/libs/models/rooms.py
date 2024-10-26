from utils import log

import redis
import os, random, json


redis_rooms = redis.Redis(
                host=os.environ.get("REDIS_HOST"),
                db=os.environ.get("REDIS_ROOMS_DB"),
                decode_responses=True
        )

redis_pubsub = redis.Redis(
            host=os.environ.get("REDIS_HOST"),
            db=os.environ.get("REDIS_PUBSUB_DB"),
            decode_responses=True
        )


ROOM_TTL = 86400 # Rooms expire after 1day of inactivity


class Room():

    USER_KEYS = {"online", "role"}
    USER_ONLINE = {0, 1} # 0 (false) for offline / 1 (True) for online
    USER_ROLE = {"player", "master", "spectator"}

    CARD_KEYS = {"player", "flipped"}
    CARD_FLIPPED = {0, 1} # 0 (false) for offline / 1 (True) for online

    def __init__(self, room_id):

        self.room_id = room_id


    def get(self):

        users = {}
        cards = {}

        for key in redis_rooms.scan_iter(f"room:{self.room_id}::*"):

            data = redis_rooms.hgetall(key)

            if "::user:" in key:
                user_id = key.split(":")[-1]  # Extract user ID from key
                users[user_id] = data

            elif "::card:" in key:
                card_id = key.split(":")[-1]  # Extract card ID from key
                cards[card_id] = data


        return {"users": users, "cards": cards}


    def set_user(self, user_id, **kwargs):

        log.info("set_user {}".format(kwargs))

        # Validate input

        params = {k: v for k, v in kwargs.items() if k in self.USER_KEYS}

        if "online" in params:
            if params["online"] not in self.USER_ONLINE:
                raise ValueError("{} not a valid value for 'online".format(params["online"]))

        if "role" in params:
            if params["role"] not in self.USER_ROLE:
                raise ValueError("{} not a valid value for 'online".format(params["role"]))

        # Update storage

        key = "room:{}::user:{}".format(self.room_id, user_id)
        res = redis_rooms.hset(key, mapping=params)

        # Publish events 

        if res == 1:
            log.info("add user {} to room {}".format(user_id, self.room_id))
            self.publish('room.joined::user:{}', user_id)

        for k, v in params.items():
            self.publish("{}.{}".format(k,v), "user:{}".format(user_id))



    def remove_user(self, user_id):

        key = "room:{}::user:{}".format(self.room_id, user_id)
        res = redis_rooms.delete(key)

        if res == 0:
            log.warning("user {} not deleted from room {} - not a member".format(user_id, self.room_id))
        else:
            log.info("delete user {} from room {}".format(user_id, self.room_id))
            self.publish('room:user.left', user_id)


    def new_round(self, players):
        
        # Validate input

        if len(players) > 10:
            raise Exception("too many users ({}): max 10".format(len(players)))


        # Clean previous round

        for key in redis_rooms.scan_iter(f"room:{self.room_id}::card:*"):

            data = redis_rooms.delete(key)


        # Define Round

        values = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
        random.shuffle(values)

        cards = {}

        i = 0
        for x in players:
            cards[x] = values[i]
            i = i+1


        # Store round properties

        for player, id in cards.items():

            key = "room:{}::card:{}".format(self.room_id, id)

            redis_rooms.hset(key, "player", player)


        # Broadcast new round event
        # self.publish('round:update', round)


    def delete(self):

        for key in redis_rooms.scan_iter(f"room:{self.room_id}::*"):
            data = redis_rooms.delete(key)

        log.info("delete room {}".format(self.room_id))



    def publish(self, key, value):

        # If value is not a string, we assume it's a more complex structure and JSON-encode it
        if not isinstance(value, str):
            value = json.dumps(value)

        # Create the message with 'key::value' format
        message = f"{key}::{value}"

        # Publish the message to the Redis channel (room_id)
        redis_pubsub.publish(self.room_id, message)
