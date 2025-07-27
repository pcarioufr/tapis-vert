# Tapis Vert - Admin Documentation

This documentation covers all administrative functionality in Tapis Vert, including user management, room management, the admin interface, and administrative APIs.

## Overview

The admin system provides tools for:
- **User Management**: Create, view, and delete users and authentication codes
- **Room Management**: Create, view, and delete game rooms
- **System Debugging**: RedisInsight for Redis data inspection
- **Data Operations**: Bulk operations and system maintenance

## Admin Access

### 🔒 Security Note
Admin routes are **only accessible from the server itself** (localhost) for security reasons. External access is completely blocked.

### Admin Interface URLs
- **Main Admin Dashboard**: `http://localhost:[TUNNEL_PORT]/admin/list` - Tables for users, rooms, and codes
- **RedisInsight**: `http://localhost:[TUNNEL_PORT]/` (port 8003) - Redis GUI for debugging

### Prerequisites
- SSH access to the server
- Understanding of the data models (User, Room, Code)
- Familiarity with Redis for debugging via RedisInsight

### 🔧 Port Configuration
**Flask Service**: The Flask container listens on **port 8001** internally
- **Direct server access**: Use `http://localhost:8001/admin/...`
- **Tunnel access**: Use `http://localhost:[TUNNEL_PORT]/admin/...` where TUNNEL_PORT is specified in the tunnel command

### Access Methods

#### 1. Tunnel Utility (Recommended)
```bash
# Create admin tunnel (access admin interface)
box -p 8000 tunnel -r 8002

# Then access admin interface at:
# http://localhost:8000/admin/list

# Create RedisInsight tunnel (access Redis GUI)
box -p 8001 tunnel -r 8003

# Then access RedisInsight at:
# http://localhost:8001/
```

#### 2. Manual SSH Tunnel
```bash
# Create tunnel manually for admin
box ssh -L 8002:localhost:8002

# Or for RedisInsight
box ssh -L 8003:localhost:8003
```

#### 3. Direct Server Access via curl
```bash
# SSH into the server
box ssh

# Use curl to interact with admin API directly
curl http://localhost:8002/admin/api/rooms
curl http://localhost:8002/admin/api/users
curl -X POST "http://localhost:8002/admin/api/rooms?name=NewRoom"
```

## Admin User Interface

### Main Dashboard (`/admin/list`)

The main admin dashboard provides tabular views with CRUD operations:

#### Features
- **Dynamic Tables**: Automatically populated tables for Users, Rooms, and Codes
- **Real-time Operations**: Create, view, and delete operations with immediate updates
- **Interactive Interface**: Click-to-action buttons for common administrative tasks

#### Interface Components
- **Tables Section**: Displays data in organized tables with headers
- **Action Buttons**: Create new entities with inline forms
- **Auto-refresh**: Tables automatically update after operations

#### Supported Operations
- **Create Users**: Add new users with specified names
- **Create Rooms**: Add new game rooms with specified names  
- **View All Entities**: Browse complete lists of users, rooms, and codes
- **Delete Entities**: Remove users, rooms, or codes (with cascade deletion for related data)

## System Debugging with RedisInsight

RedisInsight provides a professional Redis GUI for advanced debugging:

### Features
- **Key Browser**: Browse all Redis keys with filtering and search
- **Data Inspector**: View and edit Redis data structures (hashes, sets, lists, etc.)
- **CLI Integration**: Built-in Redis CLI for direct commands
- **Performance Analysis**: Memory usage, key statistics, and slow log analysis
- **Query Workbench**: Execute Redis commands with autocomplete

### Access
```bash
# Create tunnel to RedisInsight
box -p 8001 tunnel -r 8003

# Access at http://localhost:8001/
```

### Common Use Cases
- **Debug Data Issues**: Inspect actual Redis data structures
- **Performance Monitoring**: Analyze memory usage and key patterns
- **Bulk Operations**: Use CLI for complex operations
- **Data Verification**: Confirm expected data structure and relationships

## Admin API Reference

### 🔧 API Base URLs
- **Via nginx tunnel**: `http://localhost:[TUNNEL_PORT]/admin/api/...` where TUNNEL_PORT is the local port specified in tunnel command (usually 8002 for admin)
- **Direct to Flask**: `http://localhost:8001/admin/api/...` (Flask container port)

### User Management API

#### Create User
```http
POST http://localhost:8001/admin/api/users?name={user_name}
```

**Parameters:**
- `name` (query): Display name for the new user

**Response:**
```json
{
  "user123": {
    "id": "user123",
    "name": "John Doe",
    "codes": ["code456"]
  }
}
```

**Features:**
- Automatically creates associated authentication code
- Returns complete user data including relationships

#### Get User
```http
GET http://localhost:8001/admin/api/users/{user_id}
```

**Response:**
```json
{
  "id": "user123",
  "name": "John Doe",
  "codes": ["code456"],
  "rooms": ["room789"]
}
```

#### Delete User
```http
DELETE http://localhost:8001/admin/api/users/{user_id}
```

**Features:**
- **Cascade Deletion**: Automatically deletes all associated authentication codes
- **Cleanup**: Removes user from all room memberships
- **Safety**: Logs all deletion operations for audit trail

#### List All Users
```http
GET http://localhost:8001/admin/api/users
```

**Response:**
```json
{
  "user123": {
    "id": "user123",
    "name": "John Doe",
    "codes": ["code456"]
  },
  "user456": {
    "id": "user456", 
    "name": "Jane Smith",
    "codes": ["code789"]
  }
}
```

### Room Management API

#### Create Room
```http
POST http://localhost:8001/admin/api/rooms?name={room_name}
```

**Parameters:**
- `name` (query): Display name for the new room

**Response:**
```json
{
  "room123": {
    "id": "room123",
    "name": "Game Room 1",
    "round": null,
    "users": {},
    "messages": {},
    "cards": {}
  }
}
```

#### Get Room
```http
GET http://localhost:8001/admin/api/rooms/{room_id}
```

**Response:**
```json
{
  "id": "room123",
  "name": "Game Room 1",
  "round": "round456",
  "users": {
    "user123": {
      "name": "John Doe",
      "relation": {
        "role": "player",
        "status": "online"
      }
    }
  },
  "cards": {},
  "messages": {}
}
```

#### Delete Room
```http
DELETE http://localhost:8001/admin/api/rooms/{room_id}
```

**Features:**
- **Complete Cleanup**: Removes all room data including cards, messages, user associations
- **Safe Deletion**: Users remain in system, only room membership is removed

#### List All Rooms
```http
GET http://localhost:8001/admin/api/rooms
```

**Response:**
```json
{
  "room123": {
    "id": "room123",
    "name": "Game Room 1",
    "users": 3,
    "active_round": "round456"
  },
  "room789": {
    "id": "room789",
    "name": "Game Room 2", 
    "users": 1,
    "active_round": null
  }
}
```

### Authentication Code Management

#### List All Codes
```http
GET http://localhost:8001/admin/api/codes
```

**Response:**
```json
[
  {
    "id": "code123",
    "created_at": "2024-01-15T10:30:00Z",
    "user_id": "user456",
    "type": "login"
  },
  {
    "id": "code789",
    "created_at": "2024-01-15T11:45:00Z", 
    "user_id": "user123",
    "type": "login"
  }
]
```

**Features:**
- **Audit Trail**: Shows creation timestamps and associated users
- **Type Classification**: Identifies code purposes (login, etc.)
- **Relationship Data**: Links codes to specific users

## Common Administrative Tasks

### User Lifecycle Management

#### Creating a New User
1. **Via Admin UI**: 
   - Navigate to `/admin/list`
   - Enter name in Users table
   - Click create button
   
2. **Via API**:
   ```bash
   curl -X POST "http://localhost:8001/admin/api/users?name=NewUser"
   ```

#### User Cleanup
1. **Safe Deletion**: Users are deleted with cascade cleanup
2. **Code Cleanup**: Associated authentication codes are automatically removed
3. **Room Cleanup**: User memberships are removed from all rooms

### Room Lifecycle Management

#### Creating Game Rooms
1. **Via Admin UI**:
   - Navigate to `/admin/list`
   - Enter name in Rooms table
   - Click create button

2. **Via API**:
   ```bash
   curl -X POST "http://localhost:8001/admin/api/rooms?name=NewGameRoom"
   ```

#### Room Maintenance
- **Monitor Usage**: Check active users and rounds
- **Clean Empty Rooms**: Remove rooms with no active users
- **Reset Game State**: Delete and recreate rooms for fresh starts

### System Debugging

#### Redis Key Inspection with RedisInsight
1. **Access RedisInsight**:
   ```bash
   box -p 8001 tunnel -r 8003
   # Visit http://localhost:8001/
   ```

2. **Common Patterns**:
   - `user:*` - All user data
   - `room:*` - All room data  
   - `code:*` - All authentication codes
   - `*:relation:*` - All relationship data

3. **Debugging Steps**:
   - Use the key browser to find relevant keys
   - Inspect data structures in the data inspector
   - Use CLI for complex queries or bulk operations
   - Monitor memory usage and performance metrics

#### Performance Monitoring
- **Key Count Analysis**: Monitor total keys by pattern
- **Relationship Verification**: Ensure data consistency
- **Orphaned Data**: Find and clean disconnected records

## Security Considerations

### Access Control
- **Admin Routes**: Restricted to administrative users
- **Operation Logging**: All admin operations should be logged
- **Data Validation**: Input validation on all admin operations

### Data Protection
- **Cascade Deletion**: Prevents orphaned data
- **Pattern Matching**: Reduces accidental data loss
- **Backup Considerations**: Admin operations should be backed up

### Audit Trail
- **Operation Logging**: Track all administrative changes
- **User Tracking**: Associate admin operations with specific administrators
- **Change History**: Maintain records of significant data modifications

## Best Practices

### Regular Maintenance
1. **Monitor User Growth**: Track active vs inactive users
2. **Clean Expired Codes**: Remove old authentication codes
3. **Archive Old Rooms**: Clean up inactive game rooms
4. **Performance Monitoring**: Watch Redis memory usage

### Data Consistency
1. **Relationship Verification**: Regularly check data relationships
2. **Orphan Cleanup**: Remove disconnected data
3. **Index Maintenance**: Ensure efficient data retrieval

### Emergency Procedures
1. **Data Recovery**: Know how to restore from backups
2. **System Reset**: Procedures for complete data reset
3. **User Recovery**: Steps to restore accidentally deleted users

---

*This admin system provides comprehensive tools for managing the Tapis Vert application while maintaining data integrity and system performance.* 