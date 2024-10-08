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
    
    def __init__(self, room_id):

        self.room_id = room_id


    def get(self):

        if redis_rooms.exists(self.room_id):
            return redis_rooms.hgetall(self.room_id)

        else: 
            return None


    def set_user(self, user_id, status="offline"):

        if status not in ["offline", "online"]:
            raise Exception("user status should be online or offline")

        if redis_rooms.hexists(self.room_id, "user::"+user_id):
            new = False
        else:
            new = True

        res = redis_rooms.hset(self.room_id, "user::"+user_id, status)
        if res == 0:
            log.warning("user {} not added to room {} - already a member".format(user_id, self.room_id))
        else:
            log.info("add user {} to room {} with status {}".format(user_id, self.room_id, status))

        # Broadcast new user event
        if new:
            redis_pubsub.publish(self.room_id, json.dumps({'user:joined': user_id }))

        # Broadcast user status event
        redis_pubsub.publish(self.room_id, json.dumps({'user:'+status: user_id }))


    def remove_user(self, user_id):

        if not redis_rooms.hexists(self.room_id, "user::"+user_id):
            log.warning("user {} not deleted from room {} - not a member".format(user_id, self.room_id))
            return

        res = redis_rooms.hdel(self.room_id, "user::"+user_id)
        
        log.info("delete user {} from room {}".format(user_id, self.room_id))
        redis_pubsub.publish(self.room_id, json.dumps({'user:left': user_id }))


    def new_round(self, players):
        
        # Reject new round when too many users 
        if len(players) > 10:
            error = "too many users: max 10"
            raise Exception(error)

        # Shuffle cards
        values = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
        random.shuffle(values)
        cards = {}

        i = 0
        for x in players:
            cards[x] = values[i]
            i = i+1


        # Store round properties
        round = {'cards': json.dumps(cards)}

        redis_rooms.hmset(self.room_id, round)
        redis_rooms.expire(self.room_id, ROOM_TTL)

        # Broadcast new round event
        redis_pubsub.publish(self.room_id, json.dumps({'round:update': round }))


    def delete(self):

        redis_rooms.delete(self.room_id)
        log.info("delete room {}".format(self.room_id))
