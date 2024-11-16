from app.test import test_api  # Import the Blueprint from __init__.py

import flask 
import os, redis

from models import Room, User, Code, UserCode

from utils import get_logger
log = get_logger(__name__)


OK = "SUCCESS"
KO = "FAILED"
SK = "SKIPPED"

REDIS_CLIENT = redis.Redis(
    host=os.environ.get("REDIS_HOST"),
    db=os.environ.get("REDIS_DATA_DB"),
    decode_responses=True
)


def users():

    NAME = "Alice"
    user = User.create(name=NAME, nom=NAME)
    user_id = user.id

    # Assert User creation
    retrieved_user = User.get(user_id)
    tests = {
        "user:create": OK if retrieved_user else KO,
        "user:create:name": OK if retrieved_user and retrieved_user.name == NAME else KO,
        "user:create:nom": OK if retrieved_user and "nom" not in retrieved_user.data else KO,
    }

    # Assert User update
    NAME = "Alicia"
    user.name = NAME
    user.nom  = NAME
    user.save()

    retrieved_user = User.get(user_id)
    tests = {
        "user:update:name": OK if retrieved_user and retrieved_user.name == NAME else KO,
        "user:update:nom": OK if retrieved_user and "nom" not in retrieved_user.data else KO,
    }

    # Assert User deletion
    user.delete()
    retrieved_code = User.get(user_id)

    tests = tests | {
        "user:delete": OK if not retrieved_code else KO,
    }


    return tests

def codes():

    code = Code.create()
    code_id = code.id

    # Assert Code creation
    retrieved_code = Code.get(code_id)
    tests = {
        "code:create": OK if retrieved_code else KO,
    }

    # Assert Code deletion
    code.delete()
    retrieved_code = Code.get(code_id)

    tests = tests | {
        "code:delete": OK if not retrieved_code else KO,
    }

    return tests

def users_codes():

    TYPE = "login"
    TEST = "hello"

    userA = User.create(name="Alice")
    userA_id = userA.id

    # Assert whether a code can be added for Alice
    # adds it from User
    code1 = Code.create(test=TEST)
    code1_id = code1.id
    userA.codes().add(code1.id, type=TYPE)

    code1_userA, link_code1_userA = userA.codes().get(code1.id)
    userA_code1, link_userA_code1 = code1.user().get(userA.id)

    # Assert whether a second code can be added for Alice
    # adds it from Code
    code2 = Code.create()
    code2_id = code2.id
    code2.user().add(userA.id, type=TYPE)
    code2_userA, link_code2_userA = userA.codes().get(code2.id)
    userA_code2, link_code2_userA = code2.user().get(userA.id)

    # Assert whether a second user can not be added for a code
    # adds it from Code
    userB = User.create(name="Bob")
    userB_id = userB.id

    try: 
        code1.user().add(userB.id, type=TYPE)
    except Exception as e:
        log.warning(e)
        pass
    code1_userB, link_code1_userB = userB.codes().get(code1.id)
    userB_code1, link_code1_userB = code1.user().get(userB.id)

    tests = {
        "user_code:type":   OK if link_code1_userA.type == TYPE                     else KO,
        "user_code:1u1c-1": OK if code1_userA and code1_userA.id == code1.id        else KO,
        "user_code:1u1c-2": OK if userA_code1 and userA_code1.name == userA.name    else KO,
        "user_code:1u1c-3": OK if code1_userA and code1_userA.test == code1.test    else KO,
        "user_code:1u2c-1": OK if code2_userA and code2_userA.id == code2.id        else KO,
        "user_code:1u2c-2": OK if userA_code2 and userA_code2.id == userA.id        else KO,
        "user_code:2u1c-1": KO if code1_userB                                       else OK,
        "user_code:2u1c-2": KO if userB_code1                                       else OK,
    }

    # Assert code deletion results in corresponding association deletion
    code2.delete()
    retrieved_code2 = Code.get(code2_id)
    code2_userA, link_code2_userA = userA.codes().get(code2.id)

    association = UserCode.get(userA_id, code2_id)

    tests = tests | {
        "user_code:del-c1":  OK if not retrieved_code2      else KO,
        "user_code:del-c2":  OK if not code2_userA          else KO,
        "user_code:del-c3":  OK if not link_code2_userA     else KO,
        "user_code:del-c4":  OK if not association          else KO
    }

    # Assert user deletion results in corresponding association and code(s) deletion
    userA.delete()
    retrieved_code1 = Code.get(code1_id)
    code1_userA, link_code1_userA = userA.codes().get(code1_id)

    tests = tests | {
        "user_code:del-u1":  OK if not retrieved_code1      else KO,
        "user_code:del-u2":  OK if not code1_userA          else KO,
        "user_code:del-u3":  OK if not link_code2_userA     else KO,
        "user_code:del-u4":  OK if not association          else KO
    }

    return tests


@test_api.route("/invite", methods=['POST'])
def invite():

    TYPE = "login"
    TEST = "hello"

    try:
        tests = {}
        # tests.update(users())
        # tests.update(codes())
        tests.update(users_codes())

    finally:
        pass
        # teardown_test_data()

    return flask.jsonify(tests)



@test_api.route("/format/user", methods=['POST'])
def format_user():

    user = User.create(name="Alice")

    code1 = Code.create()
    user.codes().add(code1.id)

    code2 = Code.create()
    user.codes().add(code2.id)

    retrieved_user = User.get(user.id)
    
    return flask.jsonify(retrieved_user.to_dict())


@test_api.route("/format/code", methods=['POST'])
def format_code():

    user = User.create(name="Alice")

    code1 = Code.create()
    user.codes().add(code1.id)

    code2 = Code.create()
    user.codes().add(code2.id)

    retrieved_code = Code.get(code1.id)

    return flask.jsonify(retrieved_code.to_dict())


@test_api.route("/db", methods=['DELETE'])
def flush():

    REDIS_CLIENT.flushdb()
    log.info("Redis DB flushed")

    return flask.jsonify(), 204
