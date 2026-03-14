---
name: ops
description: Use when deploying, managing infrastructure, SSH access, DNS, Terraform, Docker, server operations, monitoring, or troubleshooting production issues.
user-invocable: false
---

# Tapis Vert Operations Context

## The Box CLI

All operations go through `box` (alias for `./box.sh` in the `box/` directory).
Run `box -h` for commands, `box <cmd> -h` for details on each.

### Running from Claude Code
```bash
cd box/ && ./box.sh deploy              # deploy code
cd box/ && ./box.sh ssh "docker ps"     # remote command
cd box/ && ./box.sh -d test init        # tests with debug
cd box/ && ./box.sh dns get             # DNS records
cd box/ && ./box.sh terraform plan      # infra preview
cd box/ && ./box.sh hello               # smoke test
```

Interactive commands that require the user to run:
- `box ssh` (no args) — interactive shell
- `box tunnel <local>:<remote>` — long-lived SSH tunnel

## Deployment Workflow

**Order matters. Never skip step 1.**

### 1. Push code to server
```bash
box deploy                    # Full deployment
box deploy -p webapp          # Deploy only webapp/ directory
box deploy -p nginx/nginx.conf  # Deploy single file
box deploy -n                 # Dry run (template processing only)
```
Paths are relative to `services/`. Deployment processes `{{domain}}` and `{{host}}` template variables and generates `services/.env`.

### 2. Build (only when Dockerfile or dependencies change)
```bash
box ssh "cd services && docker compose build flask"
box ssh "cd services && docker compose build websocket"
```
Builds happen on the remote server only. Never build locally.

### 3. Restart affected services
```bash
box ssh "cd services && docker compose restart flask"
box ssh "cd services && docker compose restart nginx"
# Or restart everything:
box ssh "cd services && docker compose down && docker compose up -d"
```

## Infrastructure (Terraform)

State in Terraform Cloud (org: `pcarioufr`, workspace: `tapis-vert`).

```bash
box terraform login           # Authenticate (one-time)
box terraform init            # Initialize
box terraform plan            # Preview changes
box terraform apply           # Apply (auto-updates config/.env with new IPs)
box terraform output          # Show outputs as JSON
```

After `apply`, IPs are written to `config/.env`. Run `box dns update` to sync DNS.

### Required Config
OpenStack credentials in `config/.env`: `OS_USERNAME`, `OS_PASSWORD`, `OS_TENANT_ID`, `OS_TENANT_NAME`, `SSH_PUBLIC_KEY`.

## SSH & Server Access

```bash
box ssh                       # Interactive shell
box ssh "command"             # Run remote command
box ssh -n                    # Generate new SSH key (RSA 4096)
box ssh -r                    # Reset known_hosts
```

## Admin Access (SSH Tunnel)

Admin routes are blocked by Nginx. Access via tunnel:
```bash
box tunnel 8002:8002   # Admin at http://localhost:8002/admin/list
box tunnel 8003:8003   # RedisInsight at http://localhost:8003
```

Remote ports: 8002 = admin interface, 8003 = RedisInsight.

### Admin Web Interface
- **Dashboard** (`/admin/list`): Tables for users, rooms, codes with create/delete
- **Redis debug** (`/admin/redis`): Redis data inspection

### Admin API

All endpoints below are relative to the tunnel URL (e.g. `http://localhost:8002`).

**Users:**
```
GET    /admin/api/users              # List all users
GET    /admin/api/users/{user_id}    # Get user details
POST   /admin/api/users?name=Alice   # Create user (auto-creates auth code)
DELETE /admin/api/users/{user_id}    # Delete user (cascades: codes + room memberships)
```

**Rooms:**
```
GET    /admin/api/rooms              # List all rooms
GET    /admin/api/rooms/{room_id}    # Get room details
POST   /admin/api/rooms?name=MyRoom  # Create room
DELETE /admin/api/rooms/{room_id}    # Delete room (cascades: cards, messages, memberships)
```

**Codes:**
```
GET    /admin/api/codes              # List all auth codes
```

**System:**
```
GET    /admin/api/ping               # Health check
POST   /admin/api/flush              # Flush entire Redis database
GET    /admin/api/search?pattern=*   # Search Redis keys by pattern
```

### RedisInsight
Redis GUI at tunnel port 8003. Key patterns:
- `room:*` — room data (cards, messages, round)
- `user:*` — user data
- `code:*` — authentication codes

## DNS Management

```bash
box dns get                   # Fetch current records
box dns update                # Sync A/AAAA records with config IPs
```

Required config: `INFOMANIAK_TOKEN`, `DOMAIN`, `SUBDOMAIN`.
For update: `PUBLIC_IP_V4` and/or `PUBLIC_IP_V6`.

## Docker Compose Services

| Service | Container | Port | Description |
|---|---|---|---|
| flask | flask | 8001 | Unified Flask app (gunicorn + ddtrace) |
| websocket | websocket | 8003 | FastAPI WebSocket (uvicorn) |
| redis | redis | 6379 | Data store |
| redisinsight | redisinsight | 5540 | Redis GUI |
| nginx | nginx | 80/443 | Reverse proxy, SSL, admin blocking |
| datadog | datadog | 8126 | APM agent |

## Configuration

Single config file: `config/.env` (copy from `config/example.env`).

Two sections:
- **Manual**: OpenStack credentials, app secrets, tokens
- **Auto-generated**: Terraform outputs (IPs), written after `terraform apply`

Template variables `{{domain}}` and `{{host}}` are replaced in all files during deployment. Source files are never modified.

## Testing

See the `test` skill for all test infrastructure: integration tests (`box test`), Redis ORM unit tests, and browser debugging.

## Monitoring & Troubleshooting

### Service logs
```bash
box ssh "cd services && docker compose ps"           # Service status
box ssh "cd services && docker compose logs flask"    # Flask logs
box ssh "cd services && docker compose logs nginx"    # Nginx logs
box ssh "cd services && docker compose logs websocket"  # WebSocket logs
box ssh "cd services && docker compose logs redis"    # Redis logs
```

### Server health
```bash
box ssh "df -h"               # Disk space
box ssh "free -h"             # Memory
box ssh "docker ps"           # Running containers
```

### Common issues
- **Deployment fails**: Check SSH (`box ssh "echo ok"`) and disk space
- **Template errors**: Dry run with `box deploy -n`
- **Service won't start**: Check logs, verify `.env` on server (`box ssh "cd services && cat .env"`)
- **DNS not resolving**: Verify `box dns get`, then `box dns update`
- **Admin unreachable**: Ensure tunnel is active and using correct remote port (8002)

### Datadog
- APM tracing: `ddtrace-run` wraps gunicorn in both flask and websocket services
- RUM: Frontend monitoring via client token
- Logs: Collected from all containers via labels

## Documentation References
- Full deployment guide: `docs/dev-ops/infrastructure.md`
- Architecture: `docs/dev-ops/architecture-overview.md`
