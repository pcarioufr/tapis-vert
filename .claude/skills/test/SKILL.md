---
name: test
description: Use when debugging UI issues, reproducing bugs in the browser, visually inspecting app state, running or modifying tests, or when the user asks you to look at/navigate the live webapp. Provides browser access patterns, app navigation knowledge, and test infrastructure.
user-invocable: false
---

# Tapis Vert Testing & Browser Debugging Context

## Dependencies

Browser debugging requires `agent-browser` — see README.md for install instructions.

## When to Use

Use the `agent-browser` tool to navigate the live app **only when the user explicitly asks** (e.g. "test it", "check in browser", "take a screenshot"). Do NOT automatically run browser tests after deploying — let the user verify changes themselves.

Appropriate triggers:
- The user explicitly asks you to test, check, or screenshot the app
- The user reports a visual bug and you need to see it yourself
- The user asks you to "look at" or "check" something in the app

## Live App URL

`https://tapisvert.pcariou.fr`

## Authentication

The app uses magic link codes — no passwords. To access a room as a user:

1. **Get existing codes** (requires admin tunnel — ask the user to run `box tunnel 8002:8002`):
   ```
   GET http://localhost:8002/admin/api/codes
   ```
   Response: list of `{id, user_id}` objects.

2. **Or create test data** via admin API:
   ```
   POST http://localhost:8002/admin/api/rooms?name=DebugRoom
   POST http://localhost:8002/admin/api/users?name=DebugUser
   ```
   The user creation response includes `codes[0].id`.

3. **Authenticate in browser** — navigate to:
   ```
   https://tapisvert.pcariou.fr/r/<room_id>?code_id=<code_id>
   ```
   This auto-authenticates and loads the room. The `code_id` is stripped from the URL after login.

4. **Verify auth** — after loading the room page, the account panel (top-right) should show the user's name instead of a login input.

## App Navigation

### Pages
- `/` — Landing page
- `/r/<room_id>` — Room page (main game view)
- `/r/<room_id>?code_id=<code_id>` — Room with auto-auth

### Room Page Layout
The room page is the core of the app. Key areas:

- **Table** (`#table`) — Central area with cards and user decks
- **Side panels** — Collapsible panels on the right:
  - Account panel: login/logout, user info
  - Room panel: room name, user groups by role (masters/players/watchers)
- **Chat** — Below the table, messages with emoji reactions
- **Toast notifications** (`#toasts`) — Temporary alerts (top area)

### Responsive Modes
- `<body id="S">` — Small/mobile layout (≤800px or no pointer)
- `<body id="M">` — Desktop layout

## DOM Inspection Guide

### Users
- User groups: `#panel-users-masters .user-list`, `#panel-users-players .user-list`, `#panel-users-watchers .user-list`
- Each user: `.panel-user` with `.user-name` text
- Online status: `.user-status[online]` attribute

### Cards
Cards are rendered on the table. Each card element exposes state via attributes:
- `flipped` — whether the card is face-up
- `scored` — master's score (1-10 or empty)
- Card displays: owner name, value (1-10), score

### Chat Messages
- Messages appear below the table
- Each message shows: author name, content, timestamp
- Reactions displayed as emoji badges with counts

### Score Selector
- Appears when master clicks a card to score it
- Renders as a row of selectable score values (1-10)

## WebSocket Debugging

The app maintains a WebSocket connection at `/ws/<room_id>/<user_id>`.

### Key Events to Watch
```
user:joined::<user_id>          # User entered room
user:online::<user_id>          # User came online
user:offline::<user_id>         # User went offline
user:next::<json>               # Next-round role changed ({"user_id": "...", "next": "..."})
cards:<id>:flipped::<bool>      # Card flipped/hidden
cards:<id>:peeked:<uid>::<bool> # Card peek state changed
cards:<id>:scored::<1-10>       # Card scored by master
message:new::<json>             # New chat message
message:reaction::<json>        # Emoji reaction added/removed
round:new::<json>               # New round started (promotes next→role)
```

### Message Format
All WebSocket messages use `key::value` format. Values are JSON when structured.

## Debugging Workflow

### Tunnels
When admin API access is needed, prefer asking the user to open the tunnel (e.g. `box tunnel 8002:8002`). Use matching local/remote ports when possible.

### Typical flow for reproducing a reported bug:

1. **Ask user for context**: which room, which user, what they were doing
2. **Get auth**: ask user to provide a code_id, or ask them to open the admin tunnel so you can fetch/create one
3. **Navigate**: open the room URL with code_id in browser
4. **Inspect**: take screenshots, check DOM state, look at console errors
5. **Compare**: check the API response (`/api/v1/rooms/<room_id>`) against what the DOM shows — mismatches indicate frontend rendering bugs vs backend data bugs

### Checking API state alongside browser state:
```
GET https://tapisvert.pcariou.fr/api/v1/rooms/<room_id>
```
Returns the full room object (users, cards, messages, round). Compare this with what you see in the DOM to isolate whether a bug is in the data layer or the rendering layer.

## Test Infrastructure

### Integration Tests — `box test`

Full end-to-end test via admin + public APIs over SSH. No browser involved.

```bash
box test init      # Full test suite
box test delete    # Flush Redis (wipe all data)
box -d test init   # With debug output
```

**Fixed composition:** 2 masters, 5 players, 5 watchers (12 users)

**What `test init` does** (in order):
1. Opens SSH tunnel to admin service (port 8001 → 8002)
2. Checks service accessibility (public + admin)
3. Creates 1 room and 12 users with auth codes
4. Assigns roles via `?next=` then starts round 1 (promotes next→role, deals cards)
5. Verifies round 1 state: roles, cards (5), card integrity
6. Tests permissions: master scores (ok), player scores (403), player flips other's card (403), master peeks (403), watcher messages (403), watcher starts round (403)
7. Sends 13 messages cycling through masters + players
8. Adds 12 emoji reactions including watcher reactions (watchers can react)
9. Verifies messages and reactions
10. Swaps 3 roles via `?next=`: watcher→player, player→master, master→watcher
11. Verifies two-phase separation: `next` set but `role` unchanged
12. Starts round 2 (promotes next→role)
13. Verifies promoted roles and new card distribution
14. Tests post-swap permissions: new watcher denied messaging/rounds, new player can message, new master can score
15. Cleans up SSH tunnel on exit

**Script location**: `box/cmd/test.sh`
Uses box libraries from `box/libs/` (sourced by `box.sh`). Hits `https://${SUBDOMAIN}.${DOMAIN}` (public) and `http://localhost:8001` (tunneled admin).

### Redis ORM Unit Tests — pytest

Tests for the ORM layer (`ObjectMixin`, `RelationMixin`) with its own Dockerized Redis.

```bash
# Local (spins up Docker with Redis + test container):
cd services/webapp/libs/redis-orm/tests && ./run.sh
cd services/webapp/libs/redis-orm/tests && ./run.sh --rebuild  # Force rebuild

# Remote (inside webapp container):
box ssh "cd services && docker compose exec flask pytest libs/redis-orm/tests/tests_py/ -v"
```

**Test files**:
- `services/webapp/libs/redis-orm/tests/tests_py/core_test.py` — ORM core (get, save, patch, delete, relations)
- `services/webapp/libs/redis-orm/tests/tests_py/models_test.py` — Example models (User, Post, Comment)
- `services/webapp/libs/redis-orm/tests/tests_py/conftest.py` — Fixtures (Redis connection, cleanup)

### Frontend Test Utility — `tests.js`

Minimal browser-console utility at `static/libs/tests.js`:
```js
Test.auth()  // Calls GET /api/auth/test — quick auth check from browser console
```
