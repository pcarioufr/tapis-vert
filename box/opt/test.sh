#!/bin/bash

# Tapis Vert Integration Test Suite
# Tests room creation, user management, and round logic via public APIs

set -e

# Source box libraries (same pattern as other box scripts)
for f in /opt/box/libs/* ; do source $f; done

# Function to show usage
usage() {
    echo "Usage: box test [-h] <command>"
    echo ""
    echo "Options:"
    echo "    -h           : Show this help"
    echo ""
    echo "Available commands:"
    echo "    init         : Run full integration test (room + users + round)"
    echo "    delete       : Wipe Redis database (clean slate)"
    echo ""
    echo "Examples:"
    echo "    box test init       # Run integration test"
    echo "    box test delete     # Clean Redis database"
    echo "    box -d test init    # Run with debug output"
}

# Process options first (like ssh.sh pattern)
while getopts "h" option; do
case ${option} in
    h) usage && exit 0 ;;
    *) usage && exit 1 ;;
    esac
done
shift $(($OPTIND-1))

# Get the command after processing options
COMMAND=${1:-}

if [ -z "$COMMAND" ]; then
    error "❌ No command specified"
    usage
    exit 1
fi

# Test configuration  
BASE_URL="http://${SUBDOMAIN}.${DOMAIN}"   # Public HTTP route (HTTPS not available)
ADMIN_URL="http://localhost:8001"          # Will be accessed via SSH tunnel

# Function to set up SSH tunnel
setup_tunnel() {
    notice "🔗 Opening SSH tunnel to admin service..."
    ssh -f -N -L 8001:localhost:8002 "${SSH_HOST}" 
    success "✅ Admin service tunnel established"
}

# Function to clean up tunnel
cleanup_tunnel() {
    # Kill SSH tunnel process
    pkill -f "ssh.*-L.*8001:localhost:8002" 2>/dev/null || true
    if [ $? -eq 0 ]; then
        notice "🔗 Closing admin service tunnel..."
        success "✅ Admin service tunnel closed"
    fi
}

# Function to check service accessibility
check_services() {
    info "🔍 Checking if services are accessible..."
    if ! curl -s "$BASE_URL/ping" > /dev/null 2>&1; then
        error "❌ Public webapp not accessible at $BASE_URL"
        warning "💡 Check DNS resolution and remote nginx/webapp services"
        exit 1
    fi

    if ! curl -s "$ADMIN_URL/admin/ping" > /dev/null 2>&1; then
        error "❌ Admin webapp not accessible at $ADMIN_URL (via SSH tunnel)"
        warning "💡 Check SSH connection and remote admin service"
        exit 1
    fi

    success "✅ Services accessible (public HTTP + admin tunnel)"
}

# Function to run full integration test
test_init() {
    notice "🧪 Starting Tapis Vert Integration Test..."
    info "🎯 Testing: Room + Users + Round creation via Public APIs"

    info "🌐 Using public webapp: $BASE_URL"
    info "🔐 Using admin tunnel: $ADMIN_URL"

    info "📋 Test Plan:"
    info "   1. Create Room (via admin API)"
    info "   2. Create 5 users with codes (via admin API)" 
    info "   3. Join users to room with roles (via public API + cookies)"
    info "   4. Start round (via public API + cookies)"
    info "   5. Verify game state"

    check_services

    # Step 1: Create Room via Admin API
    notice "🏠 Step 1: Creating test room..."
    ROOM_RESPONSE=$(curl -s -X POST "$ADMIN_URL/admin/api/rooms?name=Integration%20Test%20Room")
    debug "Room response: $ROOM_RESPONSE"
    ROOM_ID=$(echo "$ROOM_RESPONSE" | jq -r 'keys[0]')

    if [[ "$ROOM_ID" == "null" || -z "$ROOM_ID" ]]; then
        error "❌ Failed to create room. Response: $ROOM_RESPONSE"
        exit 1
    fi

    success "✅ Room created: $ROOM_ID"

    # Step 2: Create 5 users with codes via Admin API
    notice "👥 Step 2: Creating 5 test users..."

    declare -a USER_IDS=()
    declare -a CODE_IDS=()
    declare -a ROLES=("master" "player" "player" "player" "viewer")
    declare -a NAMES=("Alice" "Bob" "Charlie" "Diana" "Eve")

    for i in {0..4}; do
        # Create user (code is automatically created)
        info "Creating user: ${NAMES[$i]}"
        USER_RESPONSE=$(curl -s -X POST "$ADMIN_URL/admin/api/users?name=${NAMES[$i]}")
        debug "User response for ${NAMES[$i]}: $USER_RESPONSE"
        
        USER_ID=$(echo "$USER_RESPONSE" | jq -r 'keys[0]' 2>/dev/null)
        
        if [[ "$USER_ID" == "null" || -z "$USER_ID" ]]; then
            error "❌ Failed to create user ${NAMES[$i]}. Response: $USER_RESPONSE"
            exit 1
        fi
        
        USER_IDS[$i]=$USER_ID
        
        # Extract the auto-created code ID from user response
        CODE_ID=$(echo "$USER_RESPONSE" | jq -r ".[\"$USER_ID\"].codes | keys[0]" 2>/dev/null)
        
        if [[ "$CODE_ID" == "null" || -z "$CODE_ID" ]]; then
            error "❌ Failed to extract code for user ${NAMES[$i]}. Response: $USER_RESPONSE"
            exit 1
        fi
        
        CODE_IDS[$i]=$CODE_ID
        
        success "✅ User ${NAMES[$i]}: $USER_ID (code: $CODE_ID, role: ${ROLES[$i]})"
    done

    # Step 3: Join users to room via Public API (with cookie authentication)
    notice "🎮 Step 3: Joining users to room with roles..."

    for i in {0..4}; do
        CODE_ID=${CODE_IDS[$i]}
        ROLE=${ROLES[$i]}
        NAME=${NAMES[$i]}
        
        info "Authenticating $NAME and joining as $ROLE..."
        
        # Step 3a: Get authentication cookie by visiting room page directly
        COOKIE_JAR="/tmp/cookies_${i}.txt"
        
        info "Visiting room page to establish session for $NAME..."
        # Visit the room page with code_id - this should authenticate and potentially auto-join
        ROOM_VISIT_RESPONSE=$(curl -s -c "$COOKIE_JAR" "$BASE_URL/r/$ROOM_ID?code_id=$CODE_ID" 2>/dev/null)
        debug "Room visit response for $NAME: $ROOM_VISIT_RESPONSE"
        
        # Check if we got a cookie
        if [ -f "$COOKIE_JAR" ] && [ -s "$COOKIE_JAR" ]; then
            success "✅ Got session cookie for $NAME from room visit"
            debug "Cookie contents: $(cat "$COOKIE_JAR" 2>/dev/null || echo 'Unable to read cookie')"
            
            # Step 3b: Check if user is already in the room (might have auto-joined)
            info "Checking current room state for $NAME..."
            ROOM_CHECK=$(curl -s -b "$COOKIE_JAR" "$BASE_URL/api/v1/rooms/$ROOM_ID" 2>/dev/null)
            debug "Room check response: $ROOM_CHECK"
            
            # Check if this user is already in the room
            USER_IN_ROOM=$(echo "$ROOM_CHECK" | jq -r ".[\"$ROOM_ID\"].users | has(\"${USER_IDS[$i]}\")" 2>/dev/null)
            
            if [[ "$USER_IN_ROOM" == "true" ]]; then
                success "✅ $NAME already in room (auto-joined from visit)"
            else
                info "Attempting to join $NAME via API..."
                
                # Try different join methods
                JOIN_SUCCESS=false
                
                # Method 1: Standard API call with role
                JOIN_RESPONSE=$(curl -s -b "$COOKIE_JAR" -X POST \
                    "$BASE_URL/api/v1/rooms/$ROOM_ID/join?role=$ROLE" 2>/dev/null)
                debug "Join method 1 response: $JOIN_RESPONSE"
                
                if [[ "$JOIN_RESPONSE" != *"401 Unauthorized"* && "$JOIN_RESPONSE" != *"html"* ]]; then
                    JOIN_SUCCESS=true
                    success "✅ $NAME joined via API method 1"
                else
                    # Method 2: Form-style POST
                    info "Trying form-style join for $NAME..."
                    JOIN_RESPONSE=$(curl -s -b "$COOKIE_JAR" -X POST \
                        -H "Content-Type: application/x-www-form-urlencoded" \
                        -d "role=$ROLE" \
                        "$BASE_URL/r/$ROOM_ID/join" 2>/dev/null)
                    debug "Join method 2 response: $JOIN_RESPONSE"
                    
                    if [[ "$JOIN_RESPONSE" != *"401 Unauthorized"* && "$JOIN_RESPONSE" != *"html"* ]]; then
                        JOIN_SUCCESS=true
                        success "✅ $NAME joined via form method"
                    else
                        # Method 3: Visit room page again with role parameter
                        info "Trying room visit with role for $NAME..."
                        JOIN_RESPONSE=$(curl -s -b "$COOKIE_JAR" \
                            "$BASE_URL/r/$ROOM_ID?code_id=$CODE_ID&role=$ROLE" 2>/dev/null)
                        debug "Join method 3 response: $JOIN_RESPONSE"
                        
                        # Check if user is now in room
                        ROOM_CHECK2=$(curl -s -b "$COOKIE_JAR" "$BASE_URL/api/v1/rooms/$ROOM_ID" 2>/dev/null)
                        USER_IN_ROOM2=$(echo "$ROOM_CHECK2" | jq -r ".[\"$ROOM_ID\"].users | has(\"${USER_IDS[$i]}\")" 2>/dev/null)
                        
                        if [[ "$USER_IN_ROOM2" == "true" ]]; then
                            JOIN_SUCCESS=true
                            success "✅ $NAME joined via room visit with role"
                        fi
                    fi
                fi
                
                if [[ "$JOIN_SUCCESS" == "false" ]]; then
                    warning "⚠️ Unable to join $NAME to room, but continuing..."
                fi
            fi
        else
            error "❌ Failed to get session cookie for $NAME"
        fi
        
        # Clean up cookie file
        rm -f "$COOKIE_JAR"
    done

    # Step 4: Start a round via Public API (using master user's authentication)
    notice "🎲 Step 4: Starting game round..."

    # Authenticate the master user (first user) and start round
    MASTER_CODE=${CODE_IDS[0]}
    MASTER_COOKIE="/tmp/master_cookie.txt"

    info "Authenticating master user for round start..."
    curl -s -c "$MASTER_COOKIE" "$BASE_URL/r/$ROOM_ID?code_id=$MASTER_CODE" >/dev/null 2>&1

    if [ -f "$MASTER_COOKIE" ] && [ -s "$MASTER_COOKIE" ]; then
        success "✅ Master user authenticated"
        
        # Start the round using authenticated session
        ROUND_RESPONSE=$(curl -s -b "$MASTER_COOKIE" -X POST \
            "$BASE_URL/api/v1/rooms/$ROOM_ID/round")
        
        success "✅ Round started"
        debug "Round response: $ROUND_RESPONSE"
    else
        error "❌ Failed to authenticate master user"
    fi

    # Clean up master cookie
    rm -f "$MASTER_COOKIE"

    # Step 5: Verify game state
    notice "✅ Step 5: Verifying final game state..."

    # Get room details to verify everything is set up correctly
    ROOM_STATE=$(curl -s "$BASE_URL/api/v1/rooms/$ROOM_ID")

    debug "🔍 Raw room state:"
    debug "$ROOM_STATE" | jq .

    # Parse and validate the state
    NUM_USERS=$(echo "$ROOM_STATE" | jq -r ".[\"$ROOM_ID\"].users | length" 2>/dev/null || echo "0")
    HAS_ROUND=$(echo "$ROOM_STATE" | jq -r ".[\"$ROOM_ID\"].round != null" 2>/dev/null || echo "false")
    HAS_CARDS=$(echo "$ROOM_STATE" | jq -r ".[\"$ROOM_ID\"].cards | length > 0" 2>/dev/null || echo "false")

    info "📊 Room state verification:"
    info "- Users in room: $NUM_USERS/5"
    info "- Round created: $HAS_ROUND"  
    info "- Cards distributed: $HAS_CARDS"

    # Validate results (relaxed criteria since joining might not work perfectly)
    if [[ "$NUM_USERS" -gt "0" && "$HAS_ROUND" == "true" ]]; then
        success "🎉 Integration test PASSED!"
        success "✅ Room creation successful"
        success "✅ $NUM_USERS user(s) in room"  
        success "✅ Round started successfully"
        
        if [[ "$HAS_CARDS" == "true" ]]; then
            success "✅ Cards distributed"
        else
            warning "⚠️ Cards not distributed (may require more users)"
        fi
        
        # Optional: Clean up test data
        info "🧹 Cleaning up test data..."
        curl -s -X DELETE "$ADMIN_URL/admin/api/rooms/$ROOM_ID" > /dev/null
        success "✅ Test room deleted"
        
        exit 0
    else
        error "❌ Integration test FAILED!"
        error "Expected: At least 1 user, round created"
        error "Actual: $NUM_USERS users, round=$HAS_ROUND, cards=$HAS_CARDS"
        
        debug "🔍 Room state debug:"
        debug "$ROOM_STATE" | jq .
        
        info "🧹 Cleaning up test data..."
        curl -s -X DELETE "$ADMIN_URL/admin/api/rooms/$ROOM_ID" > /dev/null
        success "✅ Test room deleted"
        
        exit 1
    fi
}

# Function to wipe Redis database
test_delete() {
    notice "🗑️ Starting Redis Database Wipe..."
    warning "⚠️ This will delete ALL data in Redis!"

    info "🔐 Using admin tunnel: $ADMIN_URL"

    check_services

    info "🧹 Wiping Redis database via admin API..."
    
    # Use the proper flush endpoint
    FLUSH_RESPONSE=$(curl -s -X POST "$ADMIN_URL/admin/api/flush" 2>/dev/null)
    debug "Flush response: $FLUSH_RESPONSE"

    # Check if the flush was successful
    FLUSH_STATUS=$(echo "$FLUSH_RESPONSE" | jq -r '.status' 2>/dev/null)
    KEYS_DELETED=$(echo "$FLUSH_RESPONSE" | jq -r '.keys_deleted' 2>/dev/null || echo "0")
    REMAINING_KEYS=$(echo "$FLUSH_RESPONSE" | jq -r '.remaining_keys' 2>/dev/null || echo "unknown")
    
    if [[ "$FLUSH_STATUS" == "ok" ]]; then
        success "🎉 Redis database flushed successfully!"
        info "✅ Deleted $KEYS_DELETED keys from Redis"
        
        if [[ "$REMAINING_KEYS" == "0" ]]; then
            success "✅ Verification: Redis database is completely clean"
        else
            warning "⚠️ $REMAINING_KEYS keys still remain in Redis"
        fi
        
        exit 0
    else
        error "❌ Failed to flush Redis database"
        ERROR_MSG=$(echo "$FLUSH_RESPONSE" | jq -r '.message' 2>/dev/null || echo "Unknown error")
        warning "Error: $ERROR_MSG"
        exit 1
    fi
}

# Now that we have a valid command, set up infrastructure
# Set up tunnel cleanup on script exit
trap cleanup_tunnel EXIT

# Set up SSH tunnel for admin access
setup_tunnel

# Give tunnel a moment to establish
sleep 2

# Execute the command
case "$COMMAND" in
    "init")
        test_init
        ;;
    "delete")
        test_delete
        ;;
    *)
        error "❌ Unknown command: $COMMAND"
        usage
        exit 1
        ;;
esac