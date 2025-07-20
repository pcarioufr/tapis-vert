# Flask Public App - Build Configuration

## Purpose
User-facing application with complete game functionality.

## Features Included
- ✅ User authentication (Flask-Login)
- ✅ Room management and game logic
- ✅ QR code generation for room sharing
- ✅ Real-time WebSocket communication
- ✅ Complete UI assets and templates
- ✅ Datadog analytics integration

## Dependencies
- **gunicorn**: WSGI server
- **flask**: Web framework
- **Flask-Login**: User session management
- **redis**: Data storage and pub/sub
- **qrcode[pil]**: QR code generation for room sharing
- **nanoid**: Unique ID generation
- **ddtrace**: Datadog APM integration

## Build
```bash
docker build -t tapis-vert-public .
```

## Security
- Accessible from internet (port 8001)
- No admin functionality included
- Complete separation from admin code 