# Tapis Vert - Admin Documentation

This documentation covers all administrative functionality in Tapis Vert, including user management, room management, the admin interface, and administrative APIs.

## Overview

The admin system provides tools for:
- **User Management**: Create, view, and delete users and authentication codes
- **Room Management**: Create, view, and delete game rooms
- **System Debugging**: Redis key inspection and field deletion
- **Data Operations**: Bulk operations and system maintenance

## Admin Access

### 🔒 Security Note
Admin routes are **only accessible from the server itself** (localhost) for security reasons. External access is completely blocked.

### Admin Interface URLs
- **Main Admin Dashboard**: `http://localhost:[TUNNEL_PORT]/admin/list` - Tables for users, rooms, and codes
- **Redis Debugging Interface**: `http://localhost:[TUNNEL_PORT]/admin/redis` - Raw Redis key inspection

### Prerequisites
- SSH access to the server
- Understanding of the data models (User, Room, Code)
- Familiarity with Redis key patterns for debugging

### 🔧 Port Configuration
**Flask Service**: The Flask container listens on **port 8001** internally
- **Direct server access**: Use `http://localhost:8001/admin/...`
- **Tunnel access**: Use `http://localhost:[TUNNEL_PORT]/admin/...` where TUNNEL_PORT is specified in the tunnel command

### Access Methods

#### 1. Admin Utility (Recommended)
```bash
# Create admin tunnel (maps local port to flask port 8001)
box -p 8000 admin tunnel

# Then access admin interface at:
# http://localhost:8000/admin/list
# http://localhost:8000/admin/redis
```

#### 2. Manual SSH Tunnel
```bash
# Create tunnel manually (maps local 8001 to remote flask 8001)
box ssh -L 8001:localhost:8001

# Then access admin interface at:
# http://localhost:8001/admin/list
```

#### 3. Direct Server Access via curl
```bash
# SSH into the server
box ssh

# Use curl to interact with admin API directly on flask port 8001
curl http://localhost:8001/admin/api/rooms
curl http://localhost:8001/admin/api/users
curl -X POST "http://localhost:8001/admin/api/rooms?name=NewRoom"
```

#### 4. Test Admin API (after tunnel)
```bash
# Test admin connectivity (uses box admin command)
box admin ping
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

### Redis Debugging Interface (`/admin/redis`)

Advanced debugging interface for direct Redis operations:

#### Features
- **Key Pattern Search**: Search Redis keys using glob patterns
- **Field Pattern Deletion**: Bulk delete fields matching patterns
- **Raw Data View**: Inspect hashmap contents for debugging

#### Search Capabilities
- **Key Patterns**: Use Redis glob patterns like `user:*`, `room:*`, `code:*`
- **Field Patterns**: Target specific fields within Redis hashmaps
- **Results Display**: Shows key names and hashmap contents

#### Safety Features
- **Pattern-based Operations**: Reduces accidental data loss
- **Visual Confirmation**: Shows affected keys before operations
- **Scoped Deletion**: Delete specific fields rather than entire keys

## Admin API Reference

### 🔧 API Base URLs
- **Direct server access**: `http://localhost:8001/admin/api/...`
- **Tunnel access**: `http://localhost:[TUNNEL_PORT]/admin/api/...`

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

### Redis Operations API

#### Search Redis Keys
```http
GET http://localhost:8001/admin/api/search?pattern={key_pattern}
```

**Parameters:**
- `pattern` (query): Redis glob pattern (e.g., `user:*`, `room:*`, `code:*`)

**Response:**
```json
[
  {
    "key": "user:123",
    "hashmap": "{'id': '123', 'name': 'John Doe', 'created_at': '...'}"
  },
  {
    "key": "user:456", 
    "hashmap": "{'id': '456', 'name': 'Jane Smith', 'created_at': '...'}"
  }
]
```

**Use Cases:**
- **Debugging**: Inspect raw data structures
- **Pattern Analysis**: Find all keys matching specific patterns
- **Data Verification**: Confirm expected data structure

#### Delete Redis Fields
```http
POST http://localhost:8001/admin/api/delete_fields
```

**Request Body:**
```json
{
  "key_pattern": "user:*",
  "field_pattern": "temp_*"
}
```

**Features:**
- **Bulk Operations**: Delete multiple fields across multiple keys
- **Pattern Safety**: Uses patterns to prevent accidental total deletion
- **Selective Cleanup**: Remove specific fields while preserving key structure

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

#### Redis Key Inspection
1. **Common Patterns**:
   - `user:*` - All user data
   - `room:*` - All room data  
   - `code:*` - All authentication codes
   - `*:relation:*` - All relationship data

2. **Debugging Steps**:
   - Search with broad patterns
   - Narrow down to specific issues
   - Inspect hashmap contents
   - Identify data inconsistencies

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