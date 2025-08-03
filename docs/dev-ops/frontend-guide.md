# Frontend User Guide

This guide explains how to use the Tapis Vert application's user interface and features.

## Getting Started

### Accessing a Room

1. **Direct URL**: Visit a room using the format `/r/{room_id}`
2. **QR Code**: Scan a QR code shared by another player
3. **Magic Link**: If you have a magic link code, append `?code_id={your_code}` to automatically authenticate

### First Visit

When you first visit a room:
- You'll be assigned a temporary visitor ID
- You can view the game but have limited interaction
- Consider authenticating for full features

## User Interface Overview

### Main Game Area

The central area displays:
- **Game Table**: Where cards are displayed and interactions happen
- **Player Cards**: Your cards and other players' cards
- **Real-time Cursors**: See other players' mouse movements

### Side Panel Controls

The interface features two side panels that slide horizontally from the screen edges, each with always-visible handle tabs:

#### Left Panel - Account Management
- **Handle**: Account icon tab on the left edge, always visible
- **Cookie Preferences**: Accept/reject cookies with a toggle switch
- **Authentication**: Login with magic codes or logout button
- **Account Info**: Display current user name and status
- **Panel Width**: 20% of screen width when open

#### Right Panel - Room Management  
- **Handle**: Group icon tab on the right edge, always visible
- **Room Sharing**: Generate QR codes to invite others
- **Player List**: See all users organized by role (masters, players, watchers)
- **Panel Width**: 25% of screen width when open

#### Panel Behavior
- **Always-Visible Handles**: Icon tabs stick out from screen edges with text labels
- **Horizontal Sliding**: Panels slide in from left/right edges when handle is clicked
- **Maximum Width**: Panels open to maximum 80% screen width (with specific widths per panel)
- **Auto-Close**: Click anywhere outside the panel to close it
- **Handle Movement**: Handles are attached to panels and move with them
- **Content Height**: Panel content height adjusts to content, anchored at bottom

#### Floating Controls
- **New Round Button**: Fixed position button in lower-left corner (masters/players only)
- **Role Selection Buttons**: Three buttons in lower-right corner for choosing user role (authenticated users only)
  - Crown icon: Master role
  - Chess piece icon: Player role  
  - Glasses icon: Watcher role
- **Independent**: All floating controls positioned outside of panels for quick access

## User Roles

### Visitor (Unauthenticated)
- **Access**: Can view room and see other players
- **Limitations**: Cannot interact with cards, limited chat access
- **UI Indicators**: Shown as visitor in player list

### Player (Authenticated)
- **Access**: Full game participation
- **Abilities**: 
  - Receive cards when rounds start
  - Flip and peek at cards
  - Send chat messages
  - See detailed game state
- **UI Indicators**: Listed in "players" section

### Watcher (Authenticated)
- **Access**: Observe games without participating
- **Abilities**: 
  - View all game actions
  - Chat with other players
  - No cards assigned
- **UI Indicators**: Listed in "watchers" section

### Master (Authenticated)
- **Access**: Full game control
- **Abilities**: 
  - All player abilities
  - Start new rounds
  - Manage user roles
  - Room administration
- **UI Indicators**: Listed in "masters" section with crown icon

## Game Features

### Card Interactions

#### Viewing Cards
- Cards appear face-down by default
- Your cards show your name on the back
- Other players' cards show their names

#### Peeking at Cards
- **Single Click**: Peek at your card (corner reveal)
- **Private View**: Only you can see the peek
- **Visual Feedback**: Corner of card lifts to show value
- **Click Again**: Hide the peek

#### Flipping Cards
- **Double Click**: Flip card to reveal to everyone
- **Public View**: All players can see the card value
- **Permanent**: Card stays flipped until new round
- **Auto-hide Peek**: Peeking is disabled when card is flipped

#### Card States
Cards have visual indicators:
- **Face Down**: Default state, shows player name
- **Peeked (You)**: Corner lifted showing value to you only
- **Peeked (Others)**: Subtle visual indicator that someone else is peeking
- **Flipped**: Fully revealed showing value to everyone

### Live Communication

#### Real-time Updates
- **Instant Sync**: All actions appear immediately for all players
- **Visual Feedback**: Smooth animations for card state changes
- **Connection Status**: Automatic reconnection with user notifications

#### Chat System

The chat interface is split into two distinct areas, positioned below the game table in a vertical layout:

**Game Area (Top Section):**
- **Card Proposals**: Each player can write their proposal for their own card
- **Game-Specific**: Focused on game mechanics and card-related communication
- **Individual Input**: Personal space for game strategy and card reasoning

**Room Area (Bottom Section):**
- **General Chat**: Traditional chat interface for room-wide communication
- **Message Alignment**: Your messages appear on the right (green bubbles), others on the left (white bubbles)
- **Floating Input**: Text input and send button fixed at bottom of chat area
- **Live Display**: Messages appear instantly for all users with proper alignment
- **Author Attribution**: Each message shows sender's name and relative timestamp ("2 minutes ago")
- **Timestamp Display**: Messages show how long ago they were sent (minutes, hours, or days), automatically refreshed every minute
- **Responsive Design**: Messages adapt width on mobile devices
- **Persistent**: Messages remain visible until new round

#### Cursor Tracking
- **Live Cursors**: See other players' mouse movements on the game table
- **Color Coded**: Each player has a unique cursor color
- **Name Labels**: Cursors show player names
- **Smooth Movement**: Real-time position updates

### Room Management

#### Inviting Players
1. Click the group icon handle on the right edge to open the room panel
2. Generate QR code for the current room in the room panel
3. Share the QR code or URL with others
4. New players can scan or visit the link to join

#### Starting New Rounds
**Masters and Players only:**
1. Click the floating "New Round" button in the lower-left corner
2. Cards are automatically shuffled and redistributed
3. Previous messages are cleared
4. All players get notified

**Note**: The New Round button is only visible to authenticated users with master or player roles.

#### Managing Users
**All authenticated users can:**
- View all connected users organized by role in the right panel (room management)
- See online/offline status indicators next to user names
- Change their own role using the floating role selection buttons in the bottom-right corner

**How to change roles:**
1. Use the floating role buttons in the bottom-right corner of the screen
2. Click the desired role button: crown (master), chess piece (player), or glasses (watcher)
3. The selected button will be highlighted and your role will change immediately
4. Your user entry in the room panel will move to the appropriate role section

**Role Button Behavior:**
- Only one role can be selected at a time (radio button behavior)
- The currently selected role is visually highlighted
- Only visible to authenticated users

**Note**: The current implementation allows users to self-select their role rather than masters managing other users' roles.

## User Experience Features

### Responsive Design
- **Mobile Friendly**: Touch interactions for mobile devices
- **Adaptive Layout**: Interface adjusts to screen size
- **Touch Gestures**: Tap and double-tap work like click and double-click

### Visual Feedback
- **Animations**: Smooth transitions for card flips and peeks
- **Status Indicators**: Clear visual cues for all states
- **Color Coding**: Consistent color scheme throughout the interface
- **Icons**: Intuitive icons for all actions and states

### Notifications
- **Toast Messages**: Non-intrusive notifications for events
- **Connection Status**: Alerts when connection is lost/restored
- **Game Events**: Notifications for joins, leaves, role changes
- **Auto-dismiss**: Notifications disappear automatically

### Accessibility
- **Keyboard Navigation**: Interface supports keyboard interaction
- **Clear Indicators**: High contrast visual indicators
- **Descriptive Labels**: Screen reader friendly elements

## Technical Features

### Performance
- **Real-time Updates**: WebSocket connections for instant synchronization
- **Efficient Rendering**: Optimized for smooth 60fps interactions
- **Connection Recovery**: Automatic reconnection with state restoration

### Browser Support
- **Modern Browsers**: Works on all current browsers
- **Mobile Browsers**: Full support for mobile web browsers
- **WebSocket Support**: Requires WebSocket-enabled browser

### Data Persistence
- **Session Management**: Login state persists across page reloads
- **Room State**: Game state is maintained on the server
- **Visitor IDs**: Temporary IDs persist during session

## Troubleshooting

### Connection Issues
- **Red Toast**: Indicates connection lost, will auto-reconnect
- **Page Refresh**: Can resolve persistent connection issues
- **Browser Console**: Check for error messages

### Card Interaction Problems
- **Not Responding**: Ensure you're authenticated and have player role
- **State Sync Issues**: Wait a moment, updates may be processing
- **Multiple Clicks**: Actions are debounced, avoid rapid clicking

### Authentication Issues
- **Invalid Code**: Magic link codes can expire
- **Session Lost**: May need to re-authenticate
- **Role Changes**: Masters can update your role if needed

## Best Practices

### For Players
- **Authenticate Early**: Login for full feature access
- **Clear Communication**: Use chat to coordinate with other players
- **Respect Others**: Be mindful that others can see your actions

### For Masters
- **Observe Role Changes**: Users can self-select roles via the room panel
- **Start Rounds**: Use the floating "New Round" button when ready
- **Room Sharing**: Generate QR codes in the room panel for easy invitation

### For All Users
- **Stay Connected**: Keep browser tab active for best performance
- **Use Modern Browser**: Ensure WebSocket support for real-time features
- **Mobile Friendly**: Interface works well on mobile devices

---

*The Tapis Vert interface is designed for intuitive, real-time multiplayer gaming with rich visual feedback and seamless communication.* 