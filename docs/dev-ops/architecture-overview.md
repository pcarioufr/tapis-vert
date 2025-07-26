# Architecture Overview

This document provides a technical overview of the Tapis Vert application architecture, technology stack, and implementation details.

## System Architecture

Tapis Vert uses a **microservices architecture** with three main components:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Browser   │    │   Load Balancer  │    │      Redis      │
│                 │    │     (nginx)      │    │   Database      │
│  - Flask UI     │◄──►│                  │    │                 │
│  - WebSocket JS │    │                  │    │  - Game State   │
└─────────────────┘    └──────────────────┘    │  - Pub/Sub      │
                                ▲              │  - Sessions     │
                                │              └─────────────────┘
                                ▼                       ▲
                       ┌──────────────────┐             │
                       │  Application     │             │
                       │  Services        │◄────────────┘
                       │                  │
                       │ ┌─────────────┐  │
                       │ │ Flask App   │  │
                       │ │ (HTTP API)  │  │
                       │ └─────────────┘  │
                       │                  │
                       │ ┌─────────────┐  │
                       │ │ FastAPI     │  │
                       │ │ (WebSocket) │  │
                       │ └─────────────┘  │
                       └──────────────────┘
```

## Technology Stack

### Backend Services

#### **Flask Application (HTTP Layer)**
- **Framework**: Flask with Flask-Login for session management
- **Purpose**: Serves web pages, handles API requests, user authentication
- **Port**: 5000 (development)
- **Features**:
  - Blueprint-based modular architecture
  - Jinja2 templating for server-side rendering
  - Session-based authentication with magic links
  - RESTful API endpoints

#### **FastAPI Application (WebSocket Layer)**
- **Framework**: FastAPI with WebSocket support
- **Purpose**: Real-time communication between clients
- **Port**: 8000 (development)
- **Features**:
  - WebSocket connection management
  - Redis pub/sub integration
  - Async/await support
  - CORS middleware for cross-origin requests

#### **Redis Database**
- **Purpose**: Primary data store and message broker
- **Features**:
  - Multiple databases for different data types
  - Pub/Sub for real-time messaging
  - Custom ORM-like abstraction layer
  - Session storage

### Frontend Stack

#### **Vanilla JavaScript**
- **Framework**: Pure JavaScript (no major frameworks)
- **Architecture**: Component-based with custom Element classes
- **Features**:
  - WebSocket client with auto-reconnection
  - Real-time UI updates
  - Custom component system
  - Event-driven architecture

#### **CSS & Styling**
- **Approach**: Component-based CSS with BEM methodology
- **Features**:
  - CSS custom properties for theming
  - Responsive design with media queries
  - Animation and transition effects
  - Mobile-first design principles

## Data Architecture

### Redis Database Structure

The application uses **multiple Redis databases** for data separation:

```python
REDIS_ROUNDS_DB = 0       # Game round data
REDIS_USERS_DB = 1        # User information
REDIS_ROOMS_DB = 2        # Room data and state
REDIS_USERS_ONLINE_DB = 3 # Online presence tracking
REDIS_PUBSUB_DB = 4       # Real-time messaging
```

### Data Models

#### **External Redis ORM Package**
The application uses a custom Redis ORM implemented as an external package (`services/webapp/libs/redis-orm/`):

- **ObjectMixin**: Base class for Redis-backed objects
- **RelationMixin**: Handles relationships between objects  
- **Automatic key generation**: Uses prefixed keys for organization
- **Type conversion**: Handles JSON serialization/deserialization
- **Complete Documentation**: See package README for detailed usage, testing, and contribution guides

#### **Core Models**
```python
# User model with authentication codes
User {
    id: string,
    name: string,
    codes: Relation[UserCodes],
    rooms: Relation[UsersRooms]
}

# Room model with game state
Room {
    id: string,
    name: string,
    round: string,
    cards: dict,
    messages: dict,
    users: Relation[UsersRooms]
}

# Authentication codes for magic links
Code {
    id: string,
    user: Relation[UserCodes]
}
```

## Communication Architecture

### Real-Time Messaging

The application uses a **hybrid communication model**:

1. **HTTP for Traditional Operations**
   - Page loading and navigation
   - API calls for state changes
   - File uploads and downloads
   - Authentication

2. **WebSocket for Real-Time Updates**
   - Live game state synchronization
   - Chat messages
   - User presence tracking
   - Cursor movement tracking

### Message Flow

```
Client Action → WebSocket → FastAPI → Redis Pub/Sub → All Connected Clients
```

#### **Example Message Flow**:
1. User flips a card (client-side)
2. WebSocket sends `cards:flip::card123` to server
3. FastAPI processes message and updates Redis
4. Redis publishes update to room channel
5. All clients in room receive update instantly
6. UIs update to show flipped card

## Security Architecture

### Authentication System

#### **Magic Link Authentication**
- **Passwordless**: Users authenticate with unique codes
- **Session Management**: Flask-Login handles session persistence
- **Secure Codes**: Generated using cryptographically secure methods
- **Expiration**: Codes can be configured to expire

#### **Role-Based Access Control**
```python
Roles {
    "visitor":  # Unauthenticated, read-only access
    "watcher":  # Authenticated observer
    "player":   # Active game participant  
    "master":   # Room administrator
}
```

### Input Validation

- **Server-side validation**: All user inputs validated on backend
- **Type checking**: Redis ORM enforces data types
- **Sanitization**: XSS protection in templates
- **Rate limiting**: Debouncing prevents spam

## Deployment Architecture

### Container Strategy

The application is **containerized** for deployment:

```yaml
# Docker Compose structure
services:
  webapp:      # Flask + FastAPI applications
  redis:       # Redis database
  nginx:       # Reverse proxy and static files
  datadog:     # Monitoring and logging
```

### Environment Configuration

- **Template Processing**: Configuration files use `{{variable}}` syntax
- **Centralized Config**: Single `.env` file for all configuration
- **Deployment Scripts**: Automated template processing and deployment
- **Multi-environment**: Support for dev/staging/production

## Monitoring & Observability

### Integrated Monitoring

#### **Datadog Integration**
- **Real User Monitoring (RUM)**: Frontend performance tracking
- **Application Performance Monitoring (APM)**: Backend tracing
- **Log Collection**: Centralized logging from all components
- **Custom Metrics**: Game-specific metrics and events

#### **Mixpanel Analytics**
- **User Behavior**: Track user interactions and game events
- **Engagement Metrics**: Room usage and player activity
- **Conversion Tracking**: Authentication and retention metrics

### Distributed Tracing

```python
from ddtrace import tracer

@tracer.wrap("room.new_round")
def new_round(self):
    # Function automatically traced
    pass
```

## Performance Architecture

### Scalability Considerations

#### **Redis Performance**
- **Connection Pooling**: Efficient Redis connection management
- **Database Separation**: Logical separation prevents key collisions
- **Pub/Sub Optimization**: Dedicated database for messaging

#### **WebSocket Scaling**
- **Room-based Channels**: Users only receive relevant updates
- **Connection Management**: Automatic cleanup of disconnected clients
- **Message Throttling**: Rate limiting prevents spam

#### **Frontend Optimization**
- **Debouncing**: Prevents excessive API calls
- **Component Reuse**: Efficient DOM manipulation
- **Memory Management**: Proper cleanup of event listeners

### Caching Strategy

- **Session Caching**: Redis stores user sessions
- **Game State Caching**: Room state cached in memory
- **Static Assets**: Nginx handles static file caching

## Development Architecture

### Code Organization

```
services/webapp/
├── flask/           # Flask HTTP application
│   ├── app/         # Application modules
│   ├── static/      # Frontend assets
│   └── templates/   # Jinja2 templates
├── websocket/       # FastAPI WebSocket application
├── libs/            # Shared libraries
│   ├── redis-orm/   # External Redis ORM package (see `services/webapp/libs/redis-orm/`)
│   ├── models/      # Data models and ORM
│   └── utils/       # Utility functions
```

### Module Structure

#### **Flask Blueprints**
- `room`: Room-related web pages and API
- `auth`: Authentication system
- `admin`: Administrative tools
- `test`: Development and testing utilities

#### **WebSocket Management**
- `managers.py`: WebSocket connection management
- `asgi.py`: FastAPI application entry point

#### **Shared Libraries**
- `redis-orm/`: External Redis ORM package (see `services/webapp/libs/redis-orm/`)
- `models/`: Application-specific model definitions using the external ORM
- `utils/`: Common utilities (logging, IDs, time)

## Extensibility

### Plugin Architecture

The system is designed for extensibility:

- **Blueprint System**: Easy addition of new features
- **Component Architecture**: Reusable frontend components
- **Event System**: Pub/sub allows for feature plugins
- **Configuration Management**: Environment-based feature flags

### API Versioning

- **REST API**: Versioned endpoints (`/api/v1/`)
- **WebSocket Protocol**: Structured message format
- **Backward Compatibility**: Support for multiple client versions

---

*This architecture provides a scalable, maintainable foundation for real-time multiplayer gaming while maintaining development velocity and operational simplicity.* 