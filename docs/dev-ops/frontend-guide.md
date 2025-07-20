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

### Footer Controls

The footer contains two main sections:

#### Left Side - Account Management
- **Cookie Preferences**: Accept/reject cookies
- **Authentication**: Login with magic codes or logout
- **Account Info**: View your current name and status

#### Right Side - Room Management
- **Room Sharing**: Generate QR codes to invite others
- **Player List**: See all users organized by role (masters, players, watchers)
- **Game Controls**: Start new rounds (for masters)

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
- **Message Input**: Type and send messages to the room
- **Live Display**: Messages appear instantly for all users
- **Author Attribution**: Messages show sender's name
- **Persistent**: Messages remain visible until new round

#### Cursor Tracking
- **Live Cursors**: See other players' mouse movements on the game table
- **Color Coded**: Each player has a unique cursor color
- **Name Labels**: Cursors show player names
- **Smooth Movement**: Real-time position updates

### Room Management

#### Inviting Players
1. Click the room icon in the footer (right side)
2. Generate QR code for the current room
3. Share the QR code or URL with others
4. New players can scan or visit the link to join

#### Starting New Rounds
**Masters only:**
1. Open the room panel (right footer)
2. Click "New Round" button
3. Cards are automatically shuffled and redistributed
4. Previous messages are cleared
5. All players get notified

#### Managing Users
**Masters can:**
- View all connected users
- See online/offline status
- Change user roles between master, player, and watcher

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
- **Manage Roles**: Assign appropriate roles to users
- **Start Rounds**: Initiate new rounds when ready
- **Room Sharing**: Use QR codes for easy invitation

### For All Users
- **Stay Connected**: Keep browser tab active for best performance
- **Use Modern Browser**: Ensure WebSocket support for real-time features
- **Mobile Friendly**: Interface works well on mobile devices

---

*The Tapis Vert interface is designed for intuitive, real-time multiplayer gaming with rich visual feedback and seamless communication.* 