# Flask Admin App - Build Configuration

## Purpose
Admin-only application for system management. **Localhost access only.**

## Features Included
- ✅ User and room CRUD operations
- ✅ Redis key inspection and debugging
- ✅ System monitoring and maintenance
- ✅ Minimal UI for admin tasks

## Features Excluded (Security)
- ❌ No user authentication (localhost only)
- ❌ No QR code generation
- ❌ No client-side analytics
- ❌ No game logic or user-facing features

## Dependencies
- **gunicorn**: WSGI server
- **flask**: Web framework (minimal features)
- **redis**: Data storage access
- **nanoid**: ID utilities for admin operations
- **ddtrace**: Server-side monitoring only

## Build
```bash
docker build -t tapis-vert-admin .
```

## Security
- **LOCALHOST ONLY** (127.0.0.1:8002)
- Blocked from external access by nginx
- Minimal attack surface
- No user-facing dependencies 