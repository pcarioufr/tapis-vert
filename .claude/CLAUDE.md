# Tapis Vert Project Rules

## Project Overview
Cloud-native card game application with three layers:
- **Infrastructure**: Terraform on OpenStack (Infomaniak)
- **Application**: Docker Compose (Flask + FastAPI WebSocket + Redis + Nginx)
- **Deployment**: "The Box" — native macOS CLI toolbox (`box/box.sh`)

## The Box CLI
All operations go through the `box` CLI. Run `box -h` for commands, `box <cmd> -h` for details.

Work from the `box/` directory: `cd box/ && alias box=./box.sh`

### Running box commands
Interactive commands (bare `box ssh`, `box tunnel`) require the user to run them.

### Deployment Order (Critical)
1. `box deploy` (or `box deploy -p path`) — push code to server
2. `box ssh "cd services && docker compose build flask"` — rebuild if needed
3. `box ssh "cd services && docker compose restart flask"` — apply changes

Never skip step 1. Docker builds happen on the remote server only.

## Application Architecture
- **Flask App**: Unified app with blueprint separation
  - Public blueprint (`app/public/`): /, /api, /api/auth routes
  - Admin blueprint (`app/admin/`): /admin routes (nginx-blocked, SSH tunnel only)
  - Auth library (`libs/auth/`): Shared across blueprints
- **WebSocket**: FastAPI-based real-time communication
- **Templates**: Jinja2 — `templates/layout.jinja` base, `components/`, `admin/`, `public/`
- **Static**: `static/fonts/`, `static/libs/`, `static/styles/`

## Configuration
- Single config file: `config/.env` (manual settings + auto-generated Terraform outputs)
- `services/.env` is auto-generated during deployment
- Template variables `{{domain}}`, `{{host}}` are replaced at deploy time

## Documentation
- Game rules: `docs/game-rules.md`
- API reference: `docs/dev-ops/api-reference.md`
- Frontend guide: `docs/dev-ops/frontend-guide.md`
- Architecture: `docs/dev-ops/architecture-overview.md`
- Redis ORM: `services/webapp/libs/redis-orm/README.md`
- Admin API & access: see `ops` skill or `box tunnel -h`
