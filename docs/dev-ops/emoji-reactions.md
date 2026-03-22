# Emoji Reactions Feature

## Overview

Emoji reactions allow users to react to chat messages with emojis in real-time. The feature includes:
- Add/remove reactions by clicking on emoji bubbles
- 7 preset emoji reactions (👍 👎 ❤️ 😂 😢 😬 🤩)
- Real-time updates via WebSocket
- Backward compatibility with existing messages

## Architecture

### Backend

#### Data Model

Messages are stored as **nested dicts** in the Room model. The **ORM automatically handles flattening/unflattening**:

**Python (Room.messages dict):**
```python
{
  "abc12345": {
    "id": "abc12345",
    "timestamp": 1234567890,
    "content": "Hello!",
    "author": "user_id",
    "reactions": {
      "👍": {"user1": "True", "user2": "True"},
      "❤️": {"user3": "True"}
    }
  }
}
```

**Redis Storage (Auto-flattened by ORM):**
```
messages:abc12345:id                → "abc12345"
messages:abc12345:timestamp         → "1234567890"
messages:abc12345:content           → "Hello!"
messages:abc12345:author            → "user_id"
messages:abc12345:reactions:👍:user1 → "True"
messages:abc12345:reactions:👍:user2 → "True"
messages:abc12345:reactions:❤️:user3 → "True"
```

**API Response (Raw structure):**
```json
{
  "abc12345": {
    "id": "abc12345",
    "timestamp": "1234567890",
    "content": "Hello!",
    "author": "user_id",
    "reactions": {
      "👍": {"user1": "True", "user2": "True"},
      "❤️": {"user3": "True"}
    }
  }
}
```

#### API Endpoints

**PATCH `/api/v1/rooms/{room_id}/messages/{message_id}/react`**

Add or remove a reaction to a message.

**Authentication:** Required

**Request Body:**
```json
{
  "emoji": "👍",
  "action": "add"  // or "remove"
}
```

**Validation:**
- Emoji must be a valid emoji (max 10 Unicode code points to support compound emojis)
- Action must be "add" or "remove"
- User must be a member of the room

**Note:** Many emojis are composed of multiple Unicode code points (e.g., ❤️ = heart + variation selector). The validation allows up to 10 code points to support all standard emojis including skin tone modifiers and zero-width joiners.

**Response:**
```json
{
  "success": true
}
```

**Error Responses:**
- `400`: Invalid emoji (empty or > 10 code points) or invalid action
- `403`: User not in room
- `404`: Room or message not found

#### WebSocket Events

**`message:reaction`**

Published when a reaction is added or removed.

```json
{
  "message_id": "abc12345",
  "emoji": "👍",
  "action": "add",
  "user_id": "user1"
}
```

### Frontend

#### Components

**Message Component** (`templates/components/chat.jinja`)
- Renders reaction bubbles below each message
- Shows emoji + count for each reaction
- Highlights reactions from current user (green background)
- Displays add reaction button on hover
- Transforms raw reaction structure `{emoji: {user_id: "True"}}` to displayable format

**ChatContainer Component**
- Manages message-to-reaction mapping
- Handles API calls for toggling reactions
- Updates reaction UI via WebSocket events (no full reload needed)

#### User Interactions

1. **Add Reaction:**
   - Click on a message to reveal emoji bubbles
   - Click an empty emoji bubble to add a reaction

2. **Remove Reaction:**
   - Click on highlighted reaction bubble (green)

3. **View Reactions:**
   - Each reaction shows emoji + count
   - User's own reactions are highlighted in green
   - Emoji bubbles auto-hide when mouse leaves the message

#### CSS Styling

All reaction styles are in `static/styles/chat.css`:
- `.reactions-container`: Flexbox layout for reaction bubbles
- `.reaction-bubble`: Individual reaction with hover effects
- `.reaction-bubble.reacted`: Green highlight for user's reactions
- `.reaction-bubble.empty`: Hidden by default, shown when message is clicked (`.reactions-open`)
- `.msg-score-badge`: Score badge displayed as first item in reactions row
- Responsive styles for mobile devices

## Usage

### As a User

1. Hover over any message to see the reaction button (smile icon)
2. Click the reaction button to open emoji picker
3. Select an emoji to add it as a reaction
4. Click an existing reaction to toggle it on/off
5. All reactions update in real-time for all users

### As a Developer

#### Adding New Emojis

Edit the `AVAILABLE_EMOJIS` array in the `Message` class (`templates/components/chat.jinja`):
```javascript
static AVAILABLE_EMOJIS = ["👍", "👎", "❤️", "😂", "😢", "😬", "🤩"];
// Add more emojis to this array
```

#### Testing Reactions

```bash
# Create a message
curl -X POST http://localhost/api/v1/rooms/{room_id}/message \
  -H "Cookie: session=..." \
  -H "Content-Type: application/json" \
  -d '{"content": "Test message"}'

# Add a reaction
curl -X PATCH http://localhost/api/v1/rooms/{room_id}/messages/{message_id}/react \
  -H "Cookie: session=..." \
  -H "Content-Type: application/json" \
  -d '{"emoji": "👍", "action": "add"}'

# Remove a reaction
curl -X PATCH http://localhost/api/v1/rooms/{room_id}/messages/{message_id}/react \
  -H "Cookie: session=..." \
  -H "Content-Type: application/json" \
  -d '{"emoji": "👍", "action": "remove"}'
```

## Architecture Benefits

### Design Philosophy

**Backend: Data Layer** - The backend exposes the raw Redis data structure without transformation. This keeps the ORM simple and focused on storage concerns.

**Frontend: Presentation Layer** - The frontend transforms the raw data structure into displayable format. This separation makes debugging easier (raw data visible in Network tab) and keeps concerns separated.

### Flattened Storage Advantages

**Performance:**
- ✅ Atomic operations: Each reaction is a separate Redis field
- ✅ No JSON parsing overhead for reads/writes
- ✅ Patch operations are O(1) - no array manipulation

**Concurrency:**
- ✅ Lower conflict window: Only conflicts if exact same field modified
- ✅ Optimistic locking per-field via ORM
- ✅ Multiple users can react simultaneously without conflicts

**Simplicity:**
- ✅ Add reaction: `Room.patch(room_id, f"messages:{msg_id}:reactions:{emoji}:{user_id}", "True")`
- ✅ Remove reaction: `Room.delete_field(room_id, f"messages:{msg_id}:reactions:{emoji}:{user_id}")`
- ✅ Check if user reacted: Direct key lookup (O(1))

### Implementation Details

**Message Creation (Atomic patches):**
```python
# Each field stored separately using patch - ORM handles flattening
Room.patch(room_id, f"messages:{msg_id}:id", msg_id, add=True)
Room.patch(room_id, f"messages:{msg_id}:timestamp", str(timestamp), add=True)
Room.patch(room_id, f"messages:{msg_id}:content", content, add=True)
Room.patch(room_id, f"messages:{msg_id}:author", user_id, add=True)
```

**Reaction Toggle (Atomic operations):**
```python
# User ID as key enables atomic operations
reaction_key = f"messages:{msg_id}:reactions:{emoji}:{user_id}"
Room.patch(room_id, reaction_key, "True", add=True)  # Add
Room.delete_field(room_id, reaction_key)             # Remove (deletes key)
```

**Message Retrieval (Raw structure):**
```python
# ORM automatically unflattens when loading room
room = Room.get_by_id(room_id)
# room.messages is a dict: {msg_id: {id, content, author, reactions: {emoji: {user_id: "True"}}}}

# to_dict() returns raw structure - no transformation
room_data = room.to_dict()
# room_data[room_id]["messages"] is the same dict structure
# Frontend handles sorting and rendering
```

## Technical Notes

### Message ID Generation
- Uses `new_id(8)` from models.py
- Generates 8-character hex IDs using nanoid
- Sufficient uniqueness for room-scoped messages

### Race Conditions
- Flattened storage minimizes conflicts: Only same field writes conflict
- Redis single-threaded nature provides atomicity at field level
- Optimistic locking via ORM _version field prevents lost updates
- WebSocket broadcasts ensure all clients converge to same state

### Performance Characteristics
- **O(1) writes**: Single field patch per reaction
- **O(N) reads**: N = number of messages (reconstruction from flattened fields)
- **Storage**: More Redis fields, but negligible for chat (< 1000 messages typical)
- **Optimal for**: Real-time collaborative features with high write frequency

### Security
- User can only see/react to messages in rooms they've joined
- User authentication required for all reaction operations
- Emoji validation: Must be non-empty and ≤10 Unicode code points (prevents abuse)
- XSS-safe: Emoji rendered as text content, not HTML
- Atomic operations prevent double-reactions or race conditions

### Logging
- Debug logs show received emoji details (repr, length, bytes) for troubleshooting
- Info logs record successful reactions (user, emoji, message, room)
- Warning logs show validation failures with details

## Future Enhancements

Possible improvements:
- Custom emoji/stickers upload
- Reaction notifications
- Reaction analytics (most used emojis)
- Optimistic UI updates (show reaction before API confirms)
- Reaction animations (like Facebook)
- Tooltip showing user names who reacted
- Native emoji picker on mobile devices
- Keyboard shortcuts for quick reactions

