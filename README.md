
# Players

## TOP10

### Access Rounds

Access round `abcd-1234` as user `pierre.
https://tapis-vert.pcariou.fr/api/top10/abcd-1234?user=pierre


### Manage Rounds

(Re)Create a round `abcd-1234` with users palo, lancelot, pierre, melissa.
``` bash
curl -XPOST "https://tapis-vert.pcariou.fr/api/top10/abcd-1234?user=palo&user=lancelot&user=pierre&user=melissa"
```

Delete round `abcd-1234`.
``` bash
curl -XDELETE "https://tapis-vert.pcariou.fr/api/top10/abcd-1234f"
```

Rounds expire after 1 hour.


# Ops

"Tapis Verts" relies [The Box](https://github.com/pcarioufr/box) for its ops.

## Deploy the Infra

The Terraform files assumes access to an OpenStack public cloud (tested with Infomaniak's).
Edit [`box/.env`](box/.env).

## Run the Application

Edit [`services/.env`](services/.env).

