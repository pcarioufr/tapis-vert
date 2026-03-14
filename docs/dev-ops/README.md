# Tapis Vert - Developer & DevOps Documentation

**Tapis Vert** is a real-time multiplayer implementation of the **Top 10** party game. Players receive numbered cards (1-10) and give creative answers that match their card's position on themed scales.

## Quick Start

```bash
cd box/
alias box=./box.sh
box -h                  # See all available commands
box deploy -n           # Dry run to check templates
box deploy              # Full deployment
```

## Documentation Index

| Document | Covers |
|---|---|
| [Architecture Overview](architecture-overview.md) | System design, tech stack, data models, communication patterns |
| [Flask Applications](flask-apps.md) | Blueprint architecture, auth library, templates, deployment |
| [API Reference](api-reference.md) | REST endpoints, WebSocket protocol, data models |
| [Frontend Guide](frontend-guide.md) | JS component system, WebSocket client, state management |
| [Emoji Reactions](emoji-reactions.md) | Reaction feature: data model, API, frontend, ORM patterns |
| [Infrastructure & Deployment](infrastructure.md) | Terraform, deployment workflow, DNS, monitoring |
| [Redis ORM](../../services/webapp/libs/redis-orm/README.md) | External ORM package: ObjectMixin, RelationMixin, testing |
| Admin API | Covered in the `ops` skill (`.claude/skills/ops/SKILL.md`) |
| [Game Rules](../game-rules.md) | Top 10 rules, scoring, examples |

## Known Issues & TODOs

### API Validation
- **URGENT**: Add role validation to user PATCH endpoint (`/api/v1/rooms/<room_id>/user/<user_id>`)
  - Valid roles should be: `"master"`, `"player"`, `"watcher"`
  - Currently accepts invalid values like `"viewer"` without returning 400 error
  - **Location**: `services/webapp/flask/app/public/api/routes.py:room_user()`

### User/Card Management
- **ISSUE**: `this.eUsers[card.player_id].assignCard` error when card references non-existent user
- **Location**: `services/webapp/templates/public/room.jinja` card rendering logic
- **Fix needed**: Add safe navigation (`?.`) or user existence checks before accessing user properties

### Redis ORM
- **FIXED**: Empty marker corruption in `unflatten()` — see [redis-orm README](../../services/webapp/libs/redis-orm/README.md)
- **REMAINING**: `patch()` vs `unflatten()` inconsistency for complex nested operations
- **Current Workaround**: Messages stored as flattened fields via `patch()` to avoid nested field corruption

### Documentation
- Document all valid role values in API reference
- Add input validation examples to API documentation
- Document error codes for invalid role assignments
