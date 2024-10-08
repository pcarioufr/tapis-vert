
# Players

## TOP10

### Access Rooms

Access room `abcd-1234` as user `pierre`.
https://tapisvert.pcariou.fr/r/abcd-1234?user=pierre


### Manage Rooms

(Create room `abcd-1234` and) push a new round in room `abcd-1234`, including users `palo`, `lancelot`, `pierre`, `melissa`.
``` bash
curl -XPOST "https://tapisvert.pcariou.fr/api/v1/r/abcd-1234/round?user=palo&user=lancelot&user=pierre&user=melissa"
```

Delete room `abcd-1234`.
``` bash
curl -XDELETE "https://tapisvert.pcariou.fr/v1/abcd-1234f"
```

Rounds expire after 1 hour.


# Ops

"Tapis Verts" relies [The Box](https://github.com/pcarioufr/box) for its ops.

## Deploy the Infra

The Terraform files assumes access to an OpenStack public cloud (tested with Infomaniak's).
Edit [`box/.env`](box/.env).

## Run the Application

Edit [`services/.env`](services/.env).


# Resources

## Websockets

https://medium.com/@nandagopal05/scaling-websockets-with-pub-sub-using-python-redis-fastapi-b16392ffe291
https://medium.com/@nmjoshi/getting-started-websocket-with-fastapi-b41d244a2799

https://www.uvicorn.org/deployment/#built-in

https://www.geeksforgeeks.org/fast-api-gunicorn-vs-uvicorn/
https://www.pythoniste.fr/python/fastapi/les-differences-entre-les-frameworks-flask-et-fastapi/

https://asgi.readthedocs.io/en/latest/introduction.html
https://realpython.com/python-async-features/


https://fastapi.tiangolo.com/advanced/websockets/#handling-disconnections-and-multiple-clients
