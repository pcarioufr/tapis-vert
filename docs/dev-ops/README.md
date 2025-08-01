# Tapis Vert - Developer & DevOps Documentation

This directory contains technical documentation for developers and DevOps engineers who want to understand, develop, deploy, and operate the Tapis Vert application.

## Overview

**Tapis Vert** is a real-time multiplayer implementation of the classic **Top 10** party game. Players receive numbered cards (1-10) and give creative answers that match their card's position on themed scales.

## Quick Architecture Summary

- **Backend**: Flask (HTTP API) + FastAPI (WebSocket) + Redis (data store & pub/sub)
- **Frontend**: Vanilla JavaScript with custom component system
- **Real-time**: WebSocket-based live updates for all game interactions
- **Authentication**: Magic link-based passwordless system
- **Deployment**: Docker containers with template-based configuration

## Documentation Index

### 📋 **[API Reference](api-reference.md)**
Complete REST and WebSocket API documentation with examples:
- HTTP endpoints for room management, authentication, game actions
- WebSocket message formats for real-time communication
- Data models and error handling
- Rate limiting and security considerations

### 🏗️ **[Architecture Overview](architecture-overview.md)**  
Technical deep-dive into system design:
- Microservices architecture with component diagrams
- Technology stack details (Flask, FastAPI, Redis, JavaScript)
- Data architecture and external Redis ORM package
- Communication patterns and message flow
- Security, deployment, and monitoring setup

### 🐍 **[Flask Applications](flask-apps.md)**
Complete Flask application architecture and development guide:
- Unified Flask app: Single application with public and admin functionality
- Blueprint-based architecture: Public and admin route separation
- Nginx-based security: Admin routes protected at load balancer level
- Authentication library: Modular auth system in libs/
- Template and static asset organization
- Build dependencies, Docker configuration, and deployment workflows

### 🎨 **[Frontend Guide](frontend-guide.md)**
Frontend implementation and UI framework:
- Custom JavaScript component system
- Real-time UI updates and WebSocket client
- User interface patterns and interactions
- Performance optimizations and browser support
- Troubleshooting and development practices

### 🗄️ **[Redis ORM Package](../../services/webapp/libs/redis-orm/README.md)**
External Redis ORM package with complete documentation:
- ObjectMixin and RelationMixin patterns  
- Testing strategy and Docker test suite
- Performance considerations and known issues
- Publishing and contribution guidelines

### 🚀 **[Infrastructure & Deployment Guide](infrastructure.md)**
Complete DevOps setup and operations:
- Infrastructure provisioning with Terraform
- Application deployment with "The Box"
- SSH access and server management
- DNS management and configuration
- Monitoring, troubleshooting, and maintenance

### 🛠️ **[Admin Documentation](../admin/)**
Complete administrative tools and interfaces:
- User and room management APIs (at `/admin/api/`)
- Admin web interface documentation (at `/admin/`)
- Redis debugging and maintenance tools
- SSH tunnel access for security (localhost only)
- Common administrative tasks and best practices

## Development Setup

The application uses containerized development with "The Box" deployment system:

```bash
# From project root
cd box/
alias box=./box.sh

# Deploy for development
box deploy -n  # Dry run to check templates
box deploy     # Full deployment
```

See the main project README for complete setup instructions.

## Core Concepts

### Game Flow Implementation
1. **Room Management**: Players join rooms with unique IDs
2. **Card Distribution**: Redis-backed random assignment of 1-10 cards
3. **Real-time Sync**: WebSocket pub/sub for live game state updates
4. **Theme System**: Chat-based theme announcement (could be enhanced)
5. **Answer Collection**: Currently free-form chat (could be structured)
6. **Reveal Mechanism**: Card flip system for end-of-round reveals

### Technical Highlights
- **Custom JavaScript Framework**: No external dependencies, component-based
- **Redis-Centric**: All data in Redis with custom ORM abstraction
- **Real-time Native**: WebSocket-first architecture with auto-reconnection
- **Template-Based Config**: Environment variable replacement in all files
- **Monitoring Integration**: Datadog APM + RUM, Mixpanel analytics

## Development Guidelines

When modifying the application:

1. **Backend Changes**: Update both Flask (HTTP) and FastAPI (WebSocket) if needed
2. **Frontend Changes**: Follow the custom component patterns
3. **Data Model Changes**: Update the Redis ORM models and relationships  
4. **API Changes**: Update the API documentation
5. **Deployment**: Test template processing with `box deploy -n`

## Development Tools

- **Health Check**: Simple ping endpoint at `/ping`
- **Debug Mode**: Use `box -d` commands for verbose output
- **Log Monitoring**: Integrated Datadog logging and tracing
- **Admin Interface**: See [Admin Documentation](../admin/) for complete documentation
- **Infrastructure & Deployment**: See [Infrastructure Guide](infrastructure.md) for complete DevOps documentation

## Known Issues & TODOs

### API Validation
- **URGENT**: Add role validation to user PATCH endpoint (`/api/v1/rooms/<room_id>/user/<user_id>`)
  - Valid roles should be: `"master"`, `"player"`, `"watcher"`
  - Currently accepts invalid values like `"viewer"` without returning 400 error
  - This causes silent failures where users don't appear in rooms
  - **Location**: `services/webapp/flask/app/public/api/routes.py:room_user()`

### Documentation
- **Document all valid role values** in API reference
- **Add input validation examples** to API documentation  
- **Document error codes** for invalid role assignments

---

*For user-facing documentation about how to play the game, see [`docs/user/`](../user/)* 