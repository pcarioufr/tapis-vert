# Frontend Development Guide

Technical guide for working on the Tapis Vert frontend. For game rules, see [docs/game-rules.md](../game-rules.md).

## Architecture Overview

The frontend is a **vanilla JavaScript component system** with no build step, no external framework. Components are defined as ES6 classes in Jinja templates and wired together through a central event bus.

```
User Action → Component → API call (debounced)
                              ↓
WebSocket ← Redis pub/sub ← Server
    ↓
Event Bus → Room (model) → RoomView → Component setters → CSS attributes
```

## Key Files

| File | Responsibility |
|---|---|
| `static/libs/events.js` | Event bus: `fire()`, `listen()` with wildcard pattern matching |
| `static/libs/websocket.js` | `EventWebSocket`: auto-reconnect, `key::value` protocol, fires events |
| `static/libs/http.js` | `call()` — async fetch wrapper for REST API |
| `static/libs/misc.js` | `debounce()`, `throttle()`, `wait()`, ID generators, date formatting |
| `static/libs/cookies.js` | Cookie get/set/delete |
| `templates/public/room.jinja` | Main game page: Room model, RoomView, all component classes |
| `templates/components/` | Reusable template fragments (chat, buttons, panels, etc.) |

## Component System

### Base: Element class

All UI components extend `Element`, a thin DOM wrapper:

```javascript
class Element {
  constructor(element, eParent = null) {
    this.e = element;  // raw DOM element
    if (eParent) eParent.appendChild(this.e);
  }
  tag(name)    // set attribute (used as CSS selector)
  untag(name)  // remove attribute
  is(name)     // check attribute
  toggle(name) // toggle attribute
  select(query) // querySelector
  remove()     // remove from DOM
}
```

### Creating components

Components are defined in Jinja templates with a `<template>` tag and a JS class:

```html
<template id="t-card">
  <div class="card">
    <div class="face front"></div>
    <div class="face back"></div>
  </div>
</template>

<script>
class Card extends Element {
  constructor(card_id) {
    super(build("t-card"));  // build() clones the template
    // wire event listeners, set initial state
  }
  // Property setters update the DOM
  set value(text) { this.select('.face.front').innerText = text; }
  set flipped(bool) { bool ? this.tag('flipped') : this.untag('flipped'); }
}
</script>
```

### Styling convention

State is expressed via HTML attributes, selected with CSS:

```css
.card[flipped] .face.front { transform: rotateY(0deg); }
.card[peeked-lower] .face.back { /* corner lift animation */ }
```

## State Management

### Room (model) + RoomView (view)

```javascript
class Room {
  data = {};           // single source of truth, mirrors backend
  view = null;         // RoomView instance
  websocket = new EventWebSocket(...);

  async refresh() {
    this.data = await call("GET", `/api/v1/rooms/${this.id}`);
    this.view?.render();
  }

  connect() {
    // Subscribe to WebSocket events
    listen("Room", "user:joined", async (_, user_id) => {
      await this.refresh();
      this.view?.onUserJoined(user_id);
    });
    listen("Room", "cards:*:flipped", (_, state, eventName) => {
      const card_id = eventName.split(':')[1];
      this.data.cards[card_id].flipped = state;
      this.view?.onCardFlipped(card_id, state);
    });
    // ... more listeners
  }
}

class RoomView {
  eTable = new Table();
  eChat = new ChatContainer();
  eUsers = {};    // { user_id: UIObject }
  eCards = {};    // { card_id: Card }

  render() { /* full re-render from room.data */ }

  // Callbacks invoked by Room after data updates
  onUserJoined(user_id) { /* add user to panel */ }
  onCardFlipped(card_id, flipped) { this.eCards[card_id].flipped = flipped; }
}
```

**Data flow**: WebSocket event → Room listener → update `this.data` → call `this.view.onX()` → component setter → DOM attribute → CSS transition.

## Event Bus

Central pub/sub in `events.js`:

```javascript
fire("websocket", "cards:abc:flipped", "True");

listen("Room", "cards:*:flipped", (throwerId, data, eventName) => {
  // Wildcard matching: cards:abc:flipped, cards:xyz:flipped, etc.
});
```

- Supports `*` wildcards for pattern matching
- Event history buffer (max 100) allows late subscribers to replay
- All WebSocket messages are automatically `fire()`'d

## WebSocket Protocol

Messages use `key::value` format:

```
# Client → Server
cursor:move::75.5:25.3

# Server → Client
user:joined::user123
cards:abc:flipped::True
message:new::{"id":"x","author":"456","content":"hi"}
```

`EventWebSocket` in `websocket.js`:
- Extends native WebSocket
- Auto-reconnect with 5s delay
- Parses `key::value`, attempts JSON parse on value
- Fires all received messages to event bus
- `async send(key, value)` waits for open connection

## REST API Calls

Use the `call()` helper from `http.js`:

```javascript
// PATCH with query params
await call("PATCH", `/api/v1/rooms/${roomId}`, { "cards:abc:flipped": "True" });

// POST with JSON body
await call("POST", `/api/v1/rooms/${roomId}/message`, null, null, { content: "Hello" });
```

Interactions are debounced (300ms for card peek/flip, 100ms for cursors).

## Component Catalog

| Component | Template | Description |
|---|---|---|
| `Card` | `t-card` | Card with peek (click) and flip (double-click) |
| `Deck` | `t-deck` | User's card slot with score badge |
| `Table` | `t-table` | Card grid container |
| `ChatContainer` | `t-chat-container` | Chat area with messages and input |
| `Message` | `t-message` | Chat bubble with reactions |
| `EmojiPicker` | `t-emoji-picker` | Reaction emoji selector |
| `Panel` | `t-panel` | Sliding side panel (left/right) |
| `UserRoomPanel` | `t-user-room-panel` | User entry in room panel |
| `Button` | `t-button` | Styled button |
| `FloatingButton` | `t-floating-button` | Fixed-position action button |
| `ScoreSelector` | `t-score-selector` | Master scoring grid (1-10) |

## Adding a New Component

1. Add a `<template id="t-mycomponent">` in the appropriate Jinja file
2. Create a class extending `Element`:
   ```javascript
   class MyComponent extends Element {
     constructor() {
       super(build("t-mycomponent"));
     }
   }
   ```
3. Use property setters to update DOM state
4. Wire event listeners in `Room.connect()` if it reacts to WebSocket events
5. Add CSS styles using attribute selectors for state
6. Add render/callback methods in `RoomView` if the Room model needs to update it
