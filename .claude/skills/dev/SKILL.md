---
name: dev
description: Use when working on application code — Flask blueprints, frontend JS, WebSocket, Redis models, templates, CSS, API routes, or authentication. Provides architecture patterns, conventions, and key file locations.
user-invocable: false
---

# Tapis Vert Development Context

## Git & PR Workflow

- PRs are **squash-merged only** (enforced in repo settings). Each merged PR = one commit on `main`.
- Default squash commit message uses the **PR title**, so keep PR titles concise and descriptive.
- Commit history within a feature branch doesn't matter — it gets squashed on merge.

## Application Architecture

Single Flask app with blueprint separation, FastAPI WebSocket service, Redis data store.

### Docker Compose Services
- `flask` — unified Flask app (public + admin blueprints), port 8001, gunicorn + ddtrace
- `websocket` — FastAPI WebSocket, port 8003, uvicorn
- `redis` — data store, port 6379, two DBs: REDIS_DATA_DB=1, REDIS_PUBSUB_DB=9
- `redisinsight` — Redis GUI, port 5540 (localhost only via tunnel)
- `nginx` — reverse proxy, SSL, admin route blocking
- `datadog` — APM agent

### Key Directories
```
services/webapp/
├── flask/app/
│   ├── __init__.py          # App factory
│   ├── config.py            # Configuration
│   ├── public/              # Public blueprint
│   │   ├── api/routes.py    # REST API: /api/v1/rooms/*, /api/auth/*
│   │   └── web/routes.py    # Web routes: /r/<room_id>, /ping
│   └── admin/               # Admin blueprint
│       ├── api/routes.py    # Admin API: /admin/api/*
│       └── web/routes.py    # Admin web: /admin/list, /admin/redis
├── websocket/
│   ├── asgi.py              # FastAPI app entry point
│   └── managers.py          # WebSocket connection management
├── libs/
│   ├── auth/                # Authentication library (cross-blueprint)
│   ├── models/              # Room, User, Code models (Redis ORM)
│   ├── redis-orm/           # External ORM package (ObjectMixin, RelationMixin)
│   └── utils/               # Logging, ID generation, pub/sub helpers
├── static/
│   ├── libs/                # JS: events.js, websocket.js, http.js, misc.js, cookies.js
│   └── styles/              # CSS files (layout.css, buttons.css, chat.css, etc.)
└── templates/
    ├── layout.jinja          # Base layout
    ├── components/           # Reusable: chat.jinja, buttons.jinja, panels.jinja
    ├── public/room.jinja     # Main game page (Room model, RoomView, all components)
    └── admin/                # Admin pages: list.jinja, redis.jinja
```

## Flask Conventions

### Blueprints
- **Public** (`app/public/`): all user-facing routes. API at `/api/v1/`, auth at `/api/auth/`
- **Admin** (`app/admin/`): nginx-blocked, SSH tunnel only. API at `/admin/api/`

### Authentication
- Library in `libs/auth/` — `from auth import login, code_auth`
- Magic link codes: user visits `/r/<room_id>?code_id=<code>`, auto-authenticates
- Flask-Login for session management
- `code_id` is stripped from URL after auth (frontend does `history.replaceState`)

### Template Rendering
```python
render_template("public/room.jinja", ...)   # Public pages
render_template("admin/list.jinja", ...)    # Admin pages
```
Templates receive: `level`, `host`, `query_params`, `session`, Datadog/analytics config.

### Import Patterns
```python
from auth import code_auth          # Auth library (not a blueprint)
from .admin import admin_web        # Blueprint-relative imports
from models import Room, User       # Redis ORM models
import utils                        # Shared utilities
```

## Frontend Conventions

### Component System
- Vanilla JS, no build step, no framework
- Components extend `Element` class (thin DOM wrapper)
- Templates: `<template id="t-name">` + `class Name extends Element`
- State via HTML attributes, styled with CSS attribute selectors
- `build("t-name")` clones a template

### State Management
- `Room` class = model (holds `this.data`, manages WebSocket listeners)
- `RoomView` class = view (holds component references like `eCards`, `eUsers`)
- Flow: WebSocket event -> Room listener -> update data -> call view callback -> setter updates DOM

### Event Bus (`events.js`)
- `fire(throwerId, eventName, data)` — publish
- `listen(listenerId, pattern, callback)` — subscribe, supports `*` wildcards
- All WebSocket messages auto-fired to event bus

### WebSocket Protocol
Format: `key::value` (value JSON-parsed when possible)
```
user:joined::user123
cards:abc:flipped::True
message:new::{"id":"x","author":"456","content":"hi"}
```

### API Calls
Use `call(method, route, params, headers, body)` from `http.js`.
Card interactions debounced at 300ms, cursors at 100ms.

## Redis ORM Patterns

### Models
```python
Room  — id, name, round {id, topic}, cards (dict), messages (dict), users (Relation)
User  — id, name, codes (Relation), rooms (Relation)
Code  — id, user (Relation)
UsersRooms — role, next, status  # role=current round, next=pending for next round
```

### Key Operations
```python
Room.get_by_id(room_id)                              # Full load + unflatten
Room.patch(room_id, "cards:abc:flipped", "True")      # Atomic field update
Room.delete_field(room_id, "messages:abc:reactions:👍:user1")  # Delete field
room.to_dict()                                        # Serialize for API
```

### Known Constraint
Messages are stored as flattened fields via `patch()` (not nested `save()`) to avoid ORM unflatten corruption. See `docs/dev-ops/emoji-reactions.md` for the pattern.

## API Conventions

### Public REST API (`/api/v1/`)
- `GET /api/v1/rooms/<room_id>` — full room state
- `POST /api/v1/rooms/<room_id>/join` — join room (auth required)
- `POST /api/v1/rooms/<room_id>/round` — start new round
- `POST /api/v1/rooms/<room_id>/message` — send chat message
- `PATCH /api/v1/rooms/<room_id>` — update card state (query params)
- `PATCH /api/v1/rooms/<room_id>/user/<user_id>` — set next-round role (`?next=`)
- `PATCH /api/v1/rooms/<room_id>/cards/<card_id>/score` — score card (master only)
- `PATCH /api/v1/rooms/<room_id>/messages/<msg_id>/react` — emoji reaction

### Roles
`visitor` (unauth), `watcher`, `player`, `master`

## Documentation References
- Full API docs: `docs/dev-ops/api-reference.md`
- Flask architecture: `docs/dev-ops/flask-apps.md`
- Frontend details: `docs/dev-ops/frontend-guide.md`
- Emoji reactions: `docs/dev-ops/emoji-reactions.md`
- ORM package: `services/webapp/libs/redis-orm/README.md`
- Architecture overview: `docs/dev-ops/architecture-overview.md`
