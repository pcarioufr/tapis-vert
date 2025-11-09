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
    echo "    init         : Run full integration test (room + users + round + messaging)"
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
BASE_URL="https://${SUBDOMAIN}.${DOMAIN}"  # Public HTTPS route (HTTP redirects to HTTPS)
ADMIN_URL="http://localhost:8001"          # Will be accessed via SSH tunnel

# Function to set up SSH tunnel
setup_tunnel() {
    debug "🔗 Opening SSH tunnel to admin service..."
    ssh -f -N -L 8001:localhost:8002 "${SSH_HOST}" 
    debug "Admin service tunnel established"
}

# Function to clean up tunnel
cleanup_tunnel() {
    # Kill SSH tunnel process
    pkill -f "ssh.*-L.*8001:localhost:8002" 2>/dev/null || true
    if [ $? -eq 0 ]; then
        debug "Admin service tunnel closed"
    fi
}

# Function to check service accessibility
check_services() {
    debug "🔍 Checking if services are accessible..."
    if ! curl -s -L "$BASE_URL/ping" > /dev/null 2>&1; then
        error "Public webapp not accessible at $BASE_URL"
        info "💡 Check DNS resolution and remote nginx/webapp services"
        exit 1
    fi

    if ! curl -s "$ADMIN_URL/admin/ping" > /dev/null 2>&1; then
        error "Admin webapp not accessible at $ADMIN_URL (via SSH tunnel)"
        info "💡 Check SSH connection and remote admin service"
        exit 1
    fi

    debug "Services accessible (public HTTP + admin tunnel)"
}

# Function to run full integration test
test_init() {

    notice "Starting Tapis Vert Integration Test..."

    # Test Plan:
    # 1. Create Room (via admin API)
    # 2. Create 5 users with codes (via admin API)
    # 3. Join users to room with roles (via public API + cookies) 
    # 4. Start round (via public API + cookies)
    # 5. Test messaging system (send messages from Alice, Bob, Charlie)
    # 6. Verify game state and message storage

    check_services

    # Step 1: Create Room via Admin API
    debug "Step 1: Creating room..."

    ROOM_RESPONSE=$(curl -s -X POST "$ADMIN_URL/admin/api/rooms?name=Integration%20Test%20Room")
    debug "Room response: $ROOM_RESPONSE"
    ROOM_ID=$(echo "$ROOM_RESPONSE" | jq -r 'keys[0]')

    if [[ "$ROOM_ID" == "null" || -z "$ROOM_ID" ]]; then
        error "Failed to create room. Response: $ROOM_RESPONSE"
        exit 1
    fi

    info "New room: $ROOM_ID"

    # Step 2: Create 5 users with codes via Admin API
    debug "Step 2: Creating users..."

    declare -a USER_IDS=()
    declare -a CODE_IDS=()
    declare -a ROLES=("master" "player" "player" "player" "watcher")
    declare -a NAMES=("Alice" "Bob" "Charlie" "Diana" "Eve")

    for i in {0..4}; do
        # Create user (code is automatically created)
        USER_RESPONSE=$(curl -s -X POST "$ADMIN_URL/admin/api/users?name=${NAMES[$i]}")
        debug "User response for ${NAMES[$i]}: $USER_RESPONSE"
        
        USER_ID=$(echo "$USER_RESPONSE" | jq -r 'keys[0]' 2>/dev/null)
        
        if [[ "$USER_ID" == "null" || -z "$USER_ID" ]]; then
            error "Failed to create user ${NAMES[$i]}. Response: $USER_RESPONSE"
            exit 1
        fi
        
        USER_IDS[$i]=$USER_ID
        
        # Extract the auto-created code ID from user response
        CODE_ID=$(echo "$USER_RESPONSE" | jq -r ".[\"$USER_ID\"].codes | keys[0]" 2>/dev/null)
        
        if [[ "$CODE_ID" == "null" || -z "$CODE_ID" ]]; then
            error "Failed to extract code for user ${NAMES[$i]}. Response: $USER_RESPONSE"
            exit 1
        fi
        
        CODE_IDS[$i]=$CODE_ID
        
        info "New user ${NAMES[$i]}: $USER_ID (code: $CODE_ID, role: ${ROLES[$i]})"
    done

    # Step 3: Join users to room via Public API (with cookie authentication)
    debug "Step 3: Assigning roles to users..."

    for i in {0..4}; do
        CODE_ID=${CODE_IDS[$i]}
        ROLE=${ROLES[$i]}
        NAME=${NAMES[$i]}
        
        debug "Authenticating $NAME and joining as $ROLE..."
        
        # Step 3a: Get authentication cookie by visiting room page directly
        COOKIE_JAR="/tmp/cookies_${i}.txt"
        
        # Visit the room page with code_id - this should authenticate and potentially auto-join
        ROOM_VISIT_RESPONSE=$(curl -s -L -c "$COOKIE_JAR" "$BASE_URL/r/$ROOM_ID?code_id=$CODE_ID" 2>/dev/null)
        debug "Room visit response for $NAME: $ROOM_VISIT_RESPONSE"
        
        # Check if we got a cookie
        if [ -f "$COOKIE_JAR" ] && [ -s "$COOKIE_JAR" ]; then
            debug "Got session cookie for $NAME"
            
            # Step 1: Join room (will get default "watcher" role)
            JOIN_RESPONSE=$(curl -s -L -b "$COOKIE_JAR" -X POST \
                "$BASE_URL/api/v1/rooms/$ROOM_ID/join" 2>/dev/null)
            debug "Join response: $JOIN_RESPONSE"
            
            if [[ "$JOIN_RESPONSE" == *"401 Unauthorized"* || "$JOIN_RESPONSE" == *"html"* ]]; then
                error "Failed to join $NAME to room, skipping..."
                rm -f "$COOKIE_JAR"
                continue
            fi
            
            # Step 2: Set correct role using PATCH endpoint
            ROLE_RESPONSE=$(curl -s -L -b "$COOKIE_JAR" -X PATCH \
                "$BASE_URL/api/v1/rooms/$ROOM_ID/user/${USER_IDS[$i]}?role=$ROLE" 2>/dev/null)
            debug "Role update response: $ROLE_RESPONSE"
            
            if [[ "$ROLE_RESPONSE" == *"401 Unauthorized"* || "$ROLE_RESPONSE" == *"html"* ]]; then
                error "Failed to set role for $NAME, but continuing..."
            else
                info "$NAME assigned $ROLE role"
            fi
        else
            error "Failed to get session cookie for $NAME"
        fi
        
        # Clean up cookie file
        rm -f "$COOKIE_JAR"
    done

    # Step 4: Start a round via Public API (using master user's authentication)
    debug "Step 4: Starting game round..."

    # Authenticate the master user (first user) and start round
    MASTER_CODE=${CODE_IDS[0]}
    MASTER_COOKIE="/tmp/master_cookie.txt"

    debug "Authenticating master user for round start..."
    curl -s -L -c "$MASTER_COOKIE" "$BASE_URL/r/$ROOM_ID?code_id=$MASTER_CODE" >/dev/null 2>&1

    if [ -f "$MASTER_COOKIE" ] && [ -s "$MASTER_COOKIE" ]; then
        debug "Master user authenticated"
        
        # Start the round using authenticated session
        ROUND_RESPONSE=$(curl -s -L -b "$MASTER_COOKIE" -X POST \
            "$BASE_URL/api/v1/rooms/$ROOM_ID/round")
        
        info "New round started"
        debug "Round response: $ROUND_RESPONSE"
    else
        error "Failed to authenticate master user"
    fi

    # Clean up master cookie
    rm -f "$MASTER_COOKIE"

    # Step 5: Test messaging system
    debug "Step 5: Testing messaging system..."

    # Test messages to send - A fun conversation!
    declare -a TEST_MESSAGES=(
        "Hello" 
        "Salut, comment ça va" 
        "Yay!!!!!!!"
        "Hey everyone! Ready to play?"
        "I'm so ready! This is going to be fun 😊"
        "Count me in! What's the game?"
        "Top 10! We each get a card and try to guess the order"
        "Ooh sounds interesting! How do we win?"
        "The closest to the right order wins the round!"
        "Can't wait to see my card! Let's do this 🎮"
        "Good luck everyone!"
        "May the best player win 🏆"
        "Let's goooo!"
    )
    declare -a MESSAGE_SENDERS=(0 1 2 3 0 1 2 3 0 1 2 3 0)  # Alice, Bob, Charlie, Diana taking turns
    declare -a SENDER_NAMES=("Alice" "Bob" "Charlie" "Diana" "Alice" "Bob" "Charlie" "Diana" "Alice" "Bob" "Charlie" "Diana" "Alice")

    for i in {0..12}; do
        SENDER_INDEX=${MESSAGE_SENDERS[$i]}
        MESSAGE=${TEST_MESSAGES[$i]}
        SENDER_NAME=${SENDER_NAMES[$i]}
        SENDER_CODE=${CODE_IDS[$SENDER_INDEX]}
        
        debug "Sending message from $SENDER_NAME: '$MESSAGE'..."
        
        # Authenticate sender and send message
        SENDER_COOKIE="/tmp/sender_${i}_cookie.txt"
        
        # Get authentication cookie
        curl -s -L -c "$SENDER_COOKIE" "$BASE_URL/r/$ROOM_ID?code_id=$SENDER_CODE" >/dev/null 2>&1
        
        if [ -f "$SENDER_COOKIE" ] && [ -s "$SENDER_COOKIE" ]; then
            # Send message using authenticated session
            MESSAGE_RESPONSE=$(curl -s -L -b "$SENDER_COOKIE" -X POST \
                -H "Content-Type: application/json" \
                -d "{\"content\": \"$MESSAGE\"}" \
                "$BASE_URL/api/v1/rooms/$ROOM_ID/message")
            
            debug "Message response from $SENDER_NAME: $MESSAGE_RESPONSE"
            
            if [[ "$MESSAGE_RESPONSE" == *"401 Unauthorized"* || "$MESSAGE_RESPONSE" == *"html"* ]]; then
                error "Failed to send message from $SENDER_NAME"
            else
                info "$SENDER_NAME sent: '$MESSAGE'"
            fi
        else
            error "Failed to authenticate $SENDER_NAME for messaging"
        fi
        
        # Clean up sender cookie
        rm -f "$SENDER_COOKIE"
        
        # Small delay between messages to ensure different timestamps
        sleep 1
    done

    # Step 6: Verify game state and messages
    debug "Step 6: Verifying final game state and messages..."

    # Get room details via ADMIN API to verify everything is set up correctly
    ADMIN_ALL_ROOMS=$(curl -s "$ADMIN_URL/admin/api/rooms")
    ADMIN_ROOM_STATE=$(echo "$ADMIN_ALL_ROOMS" | jq "{\"$ROOM_ID\": .[\"$ROOM_ID\"]}")

    debug "🔍 Raw admin room state:"
    debug "$ADMIN_ROOM_STATE" | jq .

    # Parse and validate the state using admin data (more reliable)
    NUM_USERS=$(echo "$ADMIN_ROOM_STATE" | jq -r ".[\"$ROOM_ID\"].users | length" 2>/dev/null || echo "0")
    HAS_ROUND=$(echo "$ADMIN_ROOM_STATE" | jq -r ".[\"$ROOM_ID\"].round != null" 2>/dev/null || echo "false")
    # Check if cards are distributed using public API (admin API might not include full card details)
    PUBLIC_ROOM_STATE=$(curl -s -L "$BASE_URL/api/v1/rooms/$ROOM_ID")
    HAS_CARDS=$(echo "$PUBLIC_ROOM_STATE" | jq -r ".[\"$ROOM_ID\"].cards | if type == \"object\" and length > 0 then \"true\" else \"false\" end" 2>/dev/null || echo "false")
    
    # Validate card data integrity (check if all cards have complete properties)
    CARD_INTEGRITY="true"
    CARD_DETAILS=""
    if [[ "$HAS_CARDS" == "true" ]]; then
        debug "🔍 Validating card data integrity..."
        
        # Extract all cards and check their properties
        CARDS_JSON=$(echo "$PUBLIC_ROOM_STATE" | jq -r ".[\"$ROOM_ID\"].cards")
        CARD_IDS=$(echo "$CARDS_JSON" | jq -r 'keys[]' 2>/dev/null || echo "")
        
        TOTAL_CARDS=0
        COMPLETE_CARDS=0
        
        if [[ -n "$CARD_IDS" ]]; then
            for card_id in $CARD_IDS; do
                TOTAL_CARDS=$((TOTAL_CARDS + 1))
                
                # Check if card has all 4 required properties with valid values
                CARD_DATA=$(echo "$CARDS_JSON" | jq -r ".\"$card_id\"")
                
                FLIPPED=$(echo "$CARD_DATA" | jq -r '.flipped // empty')
                VALUE=$(echo "$CARD_DATA" | jq -r '.value // empty') 
                PLAYER_ID=$(echo "$CARD_DATA" | jq -r '.player_id // empty')
                PEEKED=$(echo "$CARD_DATA" | jq -r '.peeked // empty')
                
                # Count non-empty properties
                PROPS=0
                [[ -n "$FLIPPED" && "$FLIPPED" != "null" ]] && PROPS=$((PROPS + 1))
                [[ -n "$VALUE" && "$VALUE" != "null" ]] && PROPS=$((PROPS + 1))
                [[ -n "$PLAYER_ID" && "$PLAYER_ID" != "null" ]] && PROPS=$((PROPS + 1))
                [[ -n "$PEEKED" && "$PEEKED" != "null" ]] && PROPS=$((PROPS + 1))
                
                if [[ "$PROPS" == "4" ]]; then
                    COMPLETE_CARDS=$((COMPLETE_CARDS + 1))
                    debug "Card $card_id: complete (4/4 properties)"
                else
                    debug "Card $card_id: incomplete ($PROPS/4 properties)"
                    CARD_INTEGRITY="false"
                fi
            done
        fi
        
        CARD_DETAILS="$COMPLETE_CARDS/$TOTAL_CARDS"
        debug "Card integrity check: $COMPLETE_CARDS complete cards out of $TOTAL_CARDS total"
    fi

    # Verify user roles are correctly assigned
    declare -a ACTUAL_ROLES=()
    for i in {0..4}; do
        USER_ID=${USER_IDS[$i]}
        EXPECTED_ROLE=${ROLES[$i]}
        NAME=${NAMES[$i]}
        
        ACTUAL_ROLE=$(echo "$ADMIN_ROOM_STATE" | jq -r ".[\"$ROOM_ID\"].users.\"$USER_ID\".relation.role" 2>/dev/null || echo "null")
        ACTUAL_ROLES[$i]=$ACTUAL_ROLE
        
        if [[ "$ACTUAL_ROLE" == "$EXPECTED_ROLE" ]]; then
            success "$NAME role: $ACTUAL_ROLE (ok)"
        else
            error "$NAME role: nok expected $EXPECTED_ROLE, got $ACTUAL_ROLE"
        fi
    done

    # Verify messages are stored correctly
    debug "📨 Verifying message storage..."
    
    # Get messages from public API (they should be in JSON blob format)
    ROOM_MESSAGES=$(echo "$PUBLIC_ROOM_STATE" | jq -r ".[\"$ROOM_ID\"].messages" 2>/dev/null || echo "null")
    
    if [[ "$ROOM_MESSAGES" != "null" && "$ROOM_MESSAGES" != "" ]]; then
        # Parse message count
        MESSAGE_COUNT=$(echo "$ROOM_MESSAGES" | jq '. | length' 2>/dev/null || echo "0")
        
        debug "Found $MESSAGE_COUNT messages in room"
        debug "Raw messages JSON: $ROOM_MESSAGES"
        
        # Verify specific message content
        declare -a FOUND_MESSAGES=()
        for i in {0..12}; do
            EXPECTED_MESSAGE=${TEST_MESSAGES[$i]}
            SENDER_INDEX=${MESSAGE_SENDERS[$i]}
            EXPECTED_AUTHOR=${USER_IDS[$SENDER_INDEX]}
            
            # Check if message exists with correct content and author
            MESSAGE_FOUND=$(echo "$ROOM_MESSAGES" | jq -r "map(select(.content == \"$EXPECTED_MESSAGE\" and .author == \"$EXPECTED_AUTHOR\")) | length" 2>/dev/null || echo "0")
            
            if [[ "$MESSAGE_FOUND" == "1" ]]; then
                success "Message verification: '${EXPECTED_MESSAGE}' from ${SENDER_NAMES[$i]} (ok)"
                FOUND_MESSAGES[$i]="true"
            else
                error "Message verification: '${EXPECTED_MESSAGE}' from ${SENDER_NAMES[$i]} (missing)"
                FOUND_MESSAGES[$i]="false"
            fi
        done
    else
        error "No messages found in room"
        MESSAGE_COUNT=0
        FOUND_MESSAGES=("false" "false" "false" "false" "false" "false" "false" "false" "false" "false" "false" "false" "false")
    fi

    # Run independent assertions
    ASSERTIONS_PASSED=0
    TOTAL_ASSERTIONS=8  # Added 3 assertions: message count + message content + card data integrity

    # Assertion 1: Room exists and accessible
    if [[ "$ROOM_ID" != "null" && -n "$ROOM_ID" ]]; then
        success "Room creation: ok"
        ASSERTIONS_PASSED=$((ASSERTIONS_PASSED + 1))
    else
        error "Room creation: failed"
    fi

    # Assertion 2: All users joined room
    if [[ "$NUM_USERS" == "5" ]]; then
        success "Users in room: ok (5/5)"
        ASSERTIONS_PASSED=$((ASSERTIONS_PASSED + 1))
    else
        error "Users in room: failed ($NUM_USERS/5)"
    fi

    # Assertion 3: All user roles correctly assigned
    CORRECT_ROLES=0
    for i in {0..4}; do
        if [[ "${ACTUAL_ROLES[$i]}" == "${ROLES[$i]}" ]]; then
            CORRECT_ROLES=$((CORRECT_ROLES + 1))
        fi
    done
    
    if [[ "$CORRECT_ROLES" == "5" ]]; then
        success "User roles: ok (5/5)"
        ASSERTIONS_PASSED=$((ASSERTIONS_PASSED + 1))
    else
        error "User roles: failed ($CORRECT_ROLES/5)"
    fi

    # Assertion 4: Round created
    if [[ "$HAS_ROUND" == "true" ]]; then
        success "Round creation: ok"
        ASSERTIONS_PASSED=$((ASSERTIONS_PASSED + 1))
    else
        error "Round creation: failed"
    fi

    # Assertion 5: Cards distributed
    if [[ "$HAS_CARDS" == "true" ]]; then
        success "Cards distribution: ok"
        ASSERTIONS_PASSED=$((ASSERTIONS_PASSED + 1))
    else
        error "Cards distribution: failed"
    fi

    # Assertion 6: Card data integrity (NEW - detects corruption)
    if [[ "$HAS_CARDS" == "true" && "$CARD_INTEGRITY" == "true" ]]; then
        success "Card data integrity: ok ($CARD_DETAILS cards complete)"
        ASSERTIONS_PASSED=$((ASSERTIONS_PASSED + 1))
    elif [[ "$HAS_CARDS" == "true" && "$CARD_INTEGRITY" == "false" ]]; then
        error "Card data integrity: CORRUPTED ($CARD_DETAILS cards complete)"
        error "🔴 CORRUPTION DETECTED: Some cards missing properties (flipped/value/player_id/peeked)"
    else
        error "Card data integrity: failed (no cards to validate)"
    fi

    # Assertion 7: Message count correct
    if [[ "$MESSAGE_COUNT" == "13" ]]; then
        success "Message count: ok (13/13)"
        ASSERTIONS_PASSED=$((ASSERTIONS_PASSED + 1))
    else
        error "Message count: failed ($MESSAGE_COUNT/13)"
    fi

    # Assertion 8: All messages content verified
    CORRECT_MESSAGES=0
    for i in {0..12}; do
        if [[ "${FOUND_MESSAGES[$i]}" == "true" ]]; then
            CORRECT_MESSAGES=$((CORRECT_MESSAGES + 1))
        fi
    done
    
    if [[ "$CORRECT_MESSAGES" == "13" ]]; then
        success "Message content: ok (13/13)"
        ASSERTIONS_PASSED=$((ASSERTIONS_PASSED + 1))
    else
        error "Message content: failed ($CORRECT_MESSAGES/13)"
    fi

    # Overall test result
    if [[ "$ASSERTIONS_PASSED" == "$TOTAL_ASSERTIONS" ]]; then
        success "🎉 Integration test PASSED ($ASSERTIONS_PASSED/$TOTAL_ASSERTIONS assertions)"
                
        # Optional: Clean up test data
        info "Test room ready for manual testing!"

        # Show URLs for each created user
        for i in {0..4}; do
            USER_NAME=${NAMES[$i]}
            CODE_ID=${CODE_IDS[$i]}
            ROLE=${ROLES[$i]}
            USER_URL="$BASE_URL/r/$ROOM_ID?code_id=$CODE_ID"
            info "$USER_NAME ($ROLE): $USER_URL"
        done

        info "Use 'box test delete' to clean Redis when you're done testing"
        # Uncomment the line below if you want auto-cleanup:
        # curl -s -X DELETE "$ADMIN_URL/admin/api/rooms/$ROOM_ID" > /dev/null
        
        exit 0
    else
        error "❌ Integration test FAILED ($ASSERTIONS_PASSED/$TOTAL_ASSERTIONS assertions passed)"
        
        debug "🔍 Admin room state debug:"
        debug "$ADMIN_ROOM_STATE" | jq .
        
        info "Test room preserved for debugging!"
        info "Use 'box test delete' to clean Redis when you're done debugging"
        # Cleanup disabled to allow manual inspection
        # curl -s -X DELETE "$ADMIN_URL/admin/api/rooms/$ROOM_ID" > /dev/null
        
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