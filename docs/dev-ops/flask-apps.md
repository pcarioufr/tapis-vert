# Flask Application - Unified Architecture

## Overview

The Tapis Vert webapp is now a **single unified Flask application** with modular blueprint-based architecture for different functional areas:

- **Public Blueprint**: User-facing game functionality (`/` and `/api`)
- **Admin Blueprint**: System management interface (`/admin` and `/admin/api`)
- **Authentication Library**: Shared auth system in `libs/auth/`

## Architecture

### Unified Flask App (flask)

The application uses a single Flask instance with multiple blueprints for logical separation:

```
services/webapp/flask/
├── app/
│   ├── __init__.py          # App factory with centralized setup
│   ├── config.py            # Configuration management
│   ├── routines.py          # Shared render_template utilities
│   ├── admin/               # Admin blueprint
│   │   ├── __init__.py      # Blueprint definition
│   │   ├── api/             # Admin API routes (/admin/api/*)
│   │   └── web/             # Admin web routes (/admin/*)
│   │       ├── routes.py    # Route definitions
│   │       └── routines.py  # before_request handlers
│   └── public/              # Public blueprint  
│       ├── __init__.py      # Blueprint definition
│       ├── api/             # Public API routes (/api/*)
│       │   └── routes.py    # Includes auth routes (/api/auth/*)
│       └── web/             # Public web routes (/*)
│           ├── routes.py    # Route definitions
│           └── routines.py  # before_request, auth, session handling
├── static/                  # Unified static assets
│   ├── fonts/               # Font files (CabinSketch)
│   ├── libs/                # JavaScript libraries
│   └── styles/              # All CSS files
└── templates/               # Unified template system
    ├── layout.jinja         # Base layout template
    ├── components/          # Reusable template components
    ├── admin/               # Admin master templates
    │   ├── list.jinja       # Admin dashboard
    │   └── redis.jinja      # Redis debugging
    └── public/              # Public master templates
        └── room.jinja       # Game room interface
```

### Security Model

Security is handled at the **Nginx level** rather than application separation:

- **Public routes** (`/`, `/api`): Open to internet
- **Admin routes** (`/admin`, `/admin/api`): Blocked by Nginx (`deny all`)
- **Admin access**: Only via SSH tunnel (`box -p 8000 admin tunnel`)

### Blueprint Architecture

#### Public Blueprint
- **Web routes** (`/`): Game room interface, QR codes
- **API routes** (`/api`): Room management, game actions, auth endpoints
- **Auth routes** (`/api/auth/*`): Login, logout, me, test
- **Features**: Full game functionality, user authentication, real-time updates

#### Admin Blueprint  
- **Web routes** (`/admin`): Dashboard, Redis debugging interface
- **API routes** (`/admin/api`): User/room CRUD, system management
- **Security**: Localhost only (Nginx blocked + SSH tunnel required)

### Authentication Library

Authentication is now a **reusable library** in `libs/auth/`:

```python
# libs/auth/__init__.py
from auth import login, code_auth, AnonymousWebUser

# Usage in any blueprint:
from auth import code_auth
user = code_auth(code_id)
```

**Benefits**:
- ✅ **Cross-blueprint usage**: Both public and admin can use auth functions
- ✅ **No blueprint overhead**: Pure library, no route registration
- ✅ **Testable independently**: Can unit test auth logic separately
- ✅ **Professional separation**: Libraries vs blueprints serve different purposes

## Dependencies

### Core Flask Dependencies
```
Flask==3.1.0
Flask-Login==0.6.3
gunicorn==23.0.0
```

### Data & Redis
```
redis==5.2.1
-e /tmp/redis-orm  # Custom Redis ORM (editable install)
```

### Features & Utilities  
```
qrcode==8.0        # QR code generation
ddtrace==2.18.0    # Datadog APM monitoring
```

## Build & Deployment

### Docker Build
```bash
cd services/webapp/flask/
docker build -f .build/Dockerfile -t tapis-vert-flask .
```

### Build Context
- **Context**: `services/webapp/` (parent directory)
- **Dockerfile**: `flask/.build/Dockerfile`
- **Copy paths**: All relative to webapp directory

### Deployment Workflow
```bash
# 1. Deploy code to server (REQUIRED FIRST)
box deploy                    # Full deployment
box deploy -p flask/          # Deploy Flask app only

# 2. Build on remote server (AFTER code deployment)
box ssh "cd services && docker compose build flask"

# 3. Restart to apply changes
box ssh "cd services && docker compose restart flask"
```

**⚠️ Critical**: Never run `docker build` locally - builds happen on remote server only.

## Template System

### Unified Templates
All templates are now in a single directory with logical organization:

- **`layout.jinja`**: Base layout for all pages
- **`components/`**: Reusable UI components (buttons, inputs, etc.)
- **`admin/`**: Master templates called from Python (admin routes)
- **`public/`**: Master templates called from Python (public routes)

### Static Asset Management

All static files unified under `/static/`:

- **`/static/fonts/`**: Typography (CabinSketch font family)
- **`/static/libs/`**: JavaScript libraries (http.js, events.js, etc.)
- **`/static/styles/`**: All CSS files (layout.css, buttons.css, etc.)

### Query Parameter Management

Automatic URL cleanup system:

```python
# In before_request:
flask.g.query_params = dict(flask.request.args)  # Mutable copy
del flask.g.query_params['code_id']  # Remove after auth

# In render_template:
query_params=getattr(flask.g, 'query_params', dict(flask.request.args))

# Frontend automatically syncs URL:
// JavaScript updates browser URL to match backend intent
window.history.replaceState({}, '', newUrl);
```

## Development

### Local Development
```bash
# Deploy for development  
box deploy -n        # Dry run (test templates)
box deploy          # Deploy to server

# Debug mode
box -d deploy       # Verbose deployment output
```

### Admin Access
```bash
# Create SSH tunnel for admin access
box -p 8000 admin tunnel

# Visit admin interface
open http://localhost:8000/admin/list
```

### API Testing
```bash
# Test auth endpoints
curl http://localhost:8000/api/auth/test

# Test admin API (via tunnel only)
curl http://localhost:8000/admin/api/rooms
```

## Key Features

### Authentication Flow
1. **QR Code Login**: `GET /room/abc?code_id=xyz123`
2. **Auto-login**: `code_authentication()` processes code
3. **URL Cleanup**: `code_id` automatically removed from URL
4. **Session Management**: Flask-Login handles user sessions

### Real-time Integration
- **WebSocket coordination**: FastAPI WebSocket service handles real-time
- **HTTP API**: Flask handles all REST endpoints and web pages
- **Redis coordination**: Both services share Redis for state/pub-sub

### Template Variables
All templates receive comprehensive context:
```python
render_template(template,
    level=utils.LOG_LEVEL,           # Debug level
    host=app.config["HOST"],         # Host configuration  
    query_params=flask.g.query_params,  # Desired URL params
    session=flask.session,           # User session
    # ... Datadog, analytics, etc.
)
```

## Troubleshooting

### Common Issues

**Import Errors**: Ensure relative imports in Flask app:
```python
# ✅ Correct
from .admin import admin_web
from auth import code_auth

# ❌ Wrong  
from admin import admin_web
from .auth import code_auth  # (auth is now a library)
```

**Template Not Found**: Check template path updates:
```python
# ✅ New paths
render_template("admin/list.jinja")    # Admin master template
render_template("public/room.jinja")   # Public master template

# ❌ Old paths
render_template("admin/admin/_list.jinja")
render_template("public/room/_room.jinja")
```

**Static Files 404**: Use correct static paths:
```html
<!-- ✅ New unified paths -->
<link href="{{ url_for('static', filename='styles/layout.css') }}" />
<script src="{{ url_for('static', filename='libs/http.js') }}"></script>

<!-- ❌ Old nested paths -->
<link href="{{ url_for('static', filename='commons/layout.css') }}" />
```

**Auth Routes 404**: Use new API prefix:
```javascript
// ✅ New auth API routes
await call('POST', '/api/auth/login', {...})
await call('GET', '/api/auth/me')

// ❌ Old direct auth routes  
await call('POST', '/auth/login', {...})
```

### Development Tips

- **Blueprint separation**: Public and admin logic cleanly separated
- **Library pattern**: Auth can be imported by any blueprint  
- **Centralized setup**: App factory handles all initialization
- **Template organization**: Components vs master templates clearly defined
- **Security by infrastructure**: Nginx handles admin access control

---

*This unified architecture provides better maintainability while preserving security through infrastructure-level access controls.* 