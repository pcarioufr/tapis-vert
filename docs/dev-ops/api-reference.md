# API Reference

This document provides comprehensive API documentation for the Tapis Vert application.

## Base URL

All API endpoints are relative to your application's base URL:
- Local development: `http://localhost:5000`
- Production: `https://your-domain.com`

## Authentication

The application uses magic link-based authentication. Users authenticate by providing a `code_id` parameter.

### Authentication Headers

For authenticated requests, include the session cookie that's set after successful login.

## REST API Endpoints

### Health Check

#### `GET /ping`
Simple health check endpoint.

**Response:**
```json
{
  "response": "pong"
}
```

---

## Room Management

### Get Room Details

#### `GET /api/v1/rooms/{room_id}`
Retrieves detailed information about a specific room.

**Parameters:**
- `room_id` (path): Unique identifier for the room

**Response:**
```json
{
  "{room_id}": {
    "id": "room123",
    "name": "Game Room 1",
    "round": "round456",
    "cards": {
      "card1": {
        "flipped": "False",
        "player_id": "user123",
        "peeked": {
          "user123": "False",
          "user456": "True"
        },
        "value": "7"
      }
    },
    "messages": {
      "timestamp1": {
        "content": "Hello everyone!",
        "author": "user123"
      }
    },
    "users": {
      "user123": {
        "name": "Alice",
        "relation": {
          "role": "player",
          "status": "online"
        }
      }
    }
  }
}
```

### Join Room

#### `POST /api/v1/rooms/{room_id}/join`
Join a room as an authenticated user.

**Authentication:** Required

**Parameters:**
- `room_id` (path): Room to join

**Response:**
```json
{
  "room": {
    "id": "room123",
    "name": "Game Room 1",
    // ... other room data
  }
}
```

### Start New Round

#### `POST /api/v1/rooms/{room_id}/round`
Start a new game round in the room. Cards are shuffled and redistributed.

**Parameters:**
- `room_id` (path): Room identifier

**Response:**
```json
{
  "room": {
    "id": "room123",
    "round": "new_round_id",
    // ... updated room data
  }
}
```

### Send Message

#### `POST /api/v1/rooms/{room_id}/message`
Send a chat message to the room.

**Authentication:** Required

**Parameters:**
- `room_id` (path): Room identifier

**Request Body:**
```json
{
  "content": "Hello everyone!"
}
```

**Response:**
```json
// Empty response with 200 status
```

### Update Room/Card State

#### `PATCH /api/v1/rooms/{room_id}`
Update card states in the room.

**Authentication:** Required

**Parameters:**
- `room_id` (path): Room identifier

**Query Parameters:**
- `cards:{card_id}:flipped` - Set card flip state ("True"/"False")
- `cards:{card_id}:peeked:{user_id}` - Set card peek state for user ("True"/"False")

**Example:**
```
PATCH /api/v1/rooms/room123?cards:card456:flipped=True
```

**Response:**
```json
// Empty response with 200 status
```

### Update User Role

#### `PATCH /api/v1/rooms/{room_id}/user/{user_id}`
Change a user's role in the room.

**Authentication:** Required

**Parameters:**
- `room_id` (path): Room identifier
- `user_id` (path): User to update

**Query Parameters:**
- `role` - New role ("master", "player", "watcher")

**Example:**
```
PATCH /api/v1/rooms/room123/user/user456?role=player
```

**Response:**
```json
{
  "room": {
    // Updated room data with new user role
  }
}
```

---

## Authentication Endpoints

### Login with Magic Code

#### `POST /api/auth/login`
Authenticate using a magic link code.

**Query Parameters:**
- `code_id`: The authentication code from magic link

**Response:**
```json
{
  "success": true,
  "user": {
    "id": "user123",
    "name": "Alice",
    // ... user data
  }
}
```

### Get Current User

#### `GET /api/auth/me`
Get information about the currently authenticated user.

**Authentication:** Required

**Response:**
```json
{
  "user123": {
    "id": "user123", 
    "name": "Alice",
    "rooms": {
      "room123": {
        "relation": {
          "role": "player",
          "status": "online"
        }
      }
    }
  }
}
```

### Logout

#### `POST /api/auth/logout`
Log out the current user.

**Authentication:** Required

**Response:**
```json
{
  "success": true,
  "message": "Logout successful"
}
```

### Test Authentication

#### `GET /api/auth/test`
Test if authentication is working.

**Authentication:** Required

**Response:**
```json
{
  "message": "pong"
}
```

---

## Utility Endpoints

### Generate QR Code

#### `GET /api/v1/qrcode`
Generate a QR code image for sharing room links.

**Authentication:** Required

**Query Parameters:**
- `link` (required): URL to encode in QR code
- `size` (optional): QR code size (default: 8)

**Response:** PNG image file

---

## WebSocket API

### Connection

Connect to WebSocket at:
```
ws://your-domain.com/ws/{room_id}/{user_id}
```

### Message Format

All WebSocket messages follow the pattern:
```
key::value
```

Where:
- `key`: Describes the action/event type
- `value`: Data payload (can be JSON or string)

### Outgoing Messages (Client → Server)

#### Cursor Movement
```
cursor:move::75.5:25.3
```
Send cursor position relative to the game table (percentage coordinates).

#### Custom Messages
Any custom key-value pair. The server will prefix it with `user:{user_id}:` and broadcast to the room.

### Incoming Messages (Server → Client)

#### User Events
- `user:online::{user_id}` - User comes online
- `user:offline::{user_id}` - User goes offline  
- `user:joined::{user_id}` - User joins room
- `user:left::{user_id}` - User leaves room
- `user:player::{user_id}` - User becomes player
- `user:watcher::{user_id}` - User becomes watcher
- `user:master::{user_id}` - User becomes master

#### Game Events
- `round:new::{round_id}` - New round started
- `cards:{card_id}:flipped::{state}` - Card flip state changed
- `cards:{card_id}:peeked:{user_id}::{state}` - Card peek state changed

#### Chat Events
- `message:new::{message_object}` - New chat message

#### Cursor Events
- `user:{user_id}:cursor:move::{x}:{y}` - User cursor movement

### WebSocket Connection Management

The client automatically handles:
- Connection establishment
- Reconnection on disconnect
- Message queuing during reconnection
- Error handling with user notifications

---

## Error Responses

### HTTP Status Codes

- `200` - Success
- `400` - Bad Request (missing required parameters)
- `401` - Unauthorized (user not in room)
- `403` - Forbidden (invalid authentication)
- `404` - Not Found (room/user/resource doesn't exist)

### Error Response Format

```json
{
  "error": "Error description",
  "code": "ERROR_CODE"
}
```

---

## Rate Limiting

The application implements debouncing for certain operations:
- Card peek/flip actions: 300ms debounce
- Cursor movements: 100ms throttle

---

## Data Models

### Room Object
```json
{
  "id": "string",
  "name": "string", 
  "round": "string",
  "cards": {
    "card_id": {
      "flipped": "True|False",
      "player_id": "string",
      "peeked": {
        "user_id": "True|False"
      },
      "value": "string"
    }
  },
  "messages": {
    "timestamp": {
      "content": "string",
      "author": "user_id"
    }
  },
  "users": {
    "user_id": {
      "name": "string",
      "relation": {
        "role": "master|player|watcher",
        "status": "online|offline"
      }
    }
  }
}
```

### User Object
```json
{
  "id": "string",
  "name": "string",
  "rooms": {
    "room_id": {
      "relation": {
        "role": "master|player|watcher", 
        "status": "online|offline"
      }
    }
  }
}
```

### Message Object
```json
{
  "content": "string",
  "author": "user_id"
}
``` 