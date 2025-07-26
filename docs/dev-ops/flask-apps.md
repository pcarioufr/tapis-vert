# Flask Applications - Build & Architecture

## Overview

The Tapis Vert webapp consists of two separate Flask applications with distinct purposes and security models:

- **Public App**: User-facing game application 
- **Admin App**: System management interface (localhost only)

## Public App (flask-public)

### Purpose
User-facing application with complete game functionality.

### Features Included
- ✅ User authentication (Flask-Login)
- ✅ Room management and game logic
- ✅ QR code generation for room sharing
- ✅ Real-time WebSocket communication
- ✅ Complete UI assets and templates
- ✅ Datadog analytics integration

### Dependencies
- **gunicorn**: WSGI server
- **flask**: Web framework
- **Flask-Login**: User session management
- **redis**: Data storage and pub/sub
- **qrcode[pil]**: QR code generation for room sharing
- **nanoid**: Unique ID generation
- **ddtrace**: Datadog APM integration

### Build
```bash
cd services/webapp/flask-public/
docker build -t tapis-vert-public .
```

### Security
- Accessible from internet (port 8001)
- No admin functionality included
- Complete separation from admin code

## Admin App (flask-admin)

### Purpose
Admin-only application for system management. **Localhost access only.**

### Features Included
- ✅ User and room CRUD operations
- ✅ Redis key inspection and debugging
- ✅ System monitoring and maintenance
- ✅ Minimal UI for admin tasks

### Features Excluded (Security)
- ❌ No user authentication (localhost only)
- ❌ No QR code generation
- ❌ No client-side analytics
- ❌ No game logic or user-facing features

### Dependencies
- **gunicorn**: WSGI server
- **flask**: Web framework (minimal features)
- **redis**: Data storage access
- **nanoid**: ID utilities for admin operations
- **ddtrace**: Server-side monitoring only

### Build
```bash
cd services/webapp/flask-admin/
docker build -t tapis-vert-admin .
```

### Security
- **LOCALHOST ONLY** (127.0.0.1:8002)
- Blocked from external access by nginx
- Minimal attack surface
- No user-facing dependencies

## Webapp Architecture

### Directory Structure

```
services/webapp/
├── static/                    # 🎨 Shared static assets
│   ├── commons/              # Shared fonts, libs, styles
│   │   ├── fonts/           # Font files
│   │   ├── libs/            # JavaScript libraries
│   │   ├── styles/          # Common CSS components
│   │   └── layout.css       # Main layout CSS
│   ├── public/              # Public app specific assets
│   │   └── styles/          # Room/game specific CSS
│   └── admin/               # Admin app specific assets
│       └── styles/          # Admin interface CSS
├── templates/                # 🎯 Shared template system  
│   ├── commons/             # Shared template components
│   │   ├── layout.jinja     # Main layout template
│   │   ├── elements.jinja   # UI components
│   │   └── buttons.jinja    # Button components
│   ├── public/              # Public app templates
│   │   └── room/            # Game room templates
│   └── admin/               # Admin app templates
│       └── admin/           # Admin interface templates
├── flask-public/            # 🌐 Public-facing Flask app
├── flask-admin/             # 🔒 Admin-only Flask app
├── libs/                    # 📚 Shared Python libraries
└── websocket/               # 🔌 WebSocket server
```

### Template System

#### Template Organization
All templates follow a hierarchical structure:
- `commons/layout.jinja` - Main layout extended by all pages
- `commons/elements.jinja` - Shared UI components
- `public/room/_room.jinja` - Game room interface  
- `admin/admin/_list.jinja` - Admin dashboard

#### Template Inheritance
```jinja
{% extends 'commons/layout.jinja' %}     <!-- All pages extend main layout -->
{% include 'commons/elements.jinja' %}  <!-- Shared components -->
{% include 'public/room/cards.jinja' %} <!-- App-specific includes -->
```

#### Static File References
```jinja
<!-- Commons assets (shared by all apps) -->
{{ url_for('static', filename='commons/layout.css') }}
{{ url_for('static', filename='commons/libs/websocket.js') }}

<!-- App-specific assets -->
{{ url_for('static', filename='public/styles/cards.css') }}
{{ url_for('static', filename='admin/styles/list.css') }}
```

### Volume Mounts
Each Flask app gets shared access to:
- **App code**: `./flask-{app}:/flask` (read-write)
- **Shared libs**: `./libs:/opt/libs:ro` (read-only)
- **Shared static**: `./static:/flask/static:ro` (read-only)
- **Shared templates**: `./templates:/flask/templates:ro` (read-only)

## Application Separation

### Why Two Apps?

1. **Security Isolation**: Admin functionality completely separated from user-facing code
2. **Minimal Attack Surface**: Admin app has minimal dependencies and no user authentication
3. **Network Isolation**: Admin app only accessible via localhost/SSH tunnel
4. **Independent Scaling**: Each app can be scaled independently based on usage patterns

### Shared Components

Both apps share:
- Redis ORM package (`services/webapp/libs/redis-orm/`) - External package
- Application data models (`services/webapp/libs/models/`) - App-specific model definitions  
- Utility functions (`services/webapp/libs/utils/`)
- Templates and static assets via volume mounts
- Common styling through `commons/` directory

### Nginx Routing

```nginx
# Public app (internet-facing)
location / {
    proxy_pass http://webapp-public:8001;
}

# Admin app (localhost only)
server {
    listen 127.0.0.1:8002;
    location /admin/ {
        proxy_pass http://webapp-admin:8002;
    }
}
```

## Access Patterns

### Public App
- Direct internet access via nginx
- User authentication via Flask-Login
- Session management for game state

### Admin App  
- SSH tunnel required: `box -p 8000 admin tunnel`
- No authentication (localhost trust model)
- Direct Redis access for debugging
- System administration tasks

## Development

### Running Locally
```bash
# Start all services
cd services/
docker compose up -d

# Access public app
curl http://localhost:8001

# Access admin app (via tunnel)
box -p 8000 admin tunnel
curl http://localhost:8000/admin/ping
```

### Testing Admin Access
```bash
# Test admin API directly on server
box admin ping

# Test via tunnel
box -p 8000 admin tunnel
# Then in browser: http://localhost:8000/admin/list
```

## Asset Management

### Adding Shared Assets
For components used by both apps:
```bash
# Add to commons directory
echo "/* shared styles */" > services/webapp/static/commons/styles/new-component.css

# Include in commons/layout.jinja
<link rel="stylesheet" href="{{ url_for('static', filename='commons/styles/new-component.css') }}">
```

### Adding App-Specific Assets
For features specific to one app:
```bash
# Add to app-specific directory
echo "/* public only */" > services/webapp/static/public/styles/new-feature.css

# Include in app-specific template
<link rel="stylesheet" href="{{ url_for('static', filename='public/styles/new-feature.css') }}">
```

### Benefits of Shared Architecture
1. **🎯 Single Source of Truth**: Shared assets in one place
2. **🔄 No Duplication**: Common styles/scripts shared between apps
3. **🎨 Easy Theming**: Update commons to change both apps
4. **📦 Clean Separation**: App-specific assets clearly organized
5. **🚀 Fast Development**: Changes apply to both apps instantly

## Troubleshooting

### Template Not Found
- Check if template path uses correct subdirectory (`public/`, `admin/`, `commons/`)
- Verify template extends `commons/layout.jinja`

### Static Asset 404
- Confirm asset is in correct subdirectory
- Check `url_for('static', filename='...')` path includes subdirectory

### Hot Reload Issues
- Restart containers to pick up new volume mounts
- Check Docker volume mounts in `compose.yml` 