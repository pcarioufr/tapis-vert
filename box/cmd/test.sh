#!/bin/bash

# Tapis Vert Integration Test Suite
# Tests room creation, user management, and round logic via public APIs

set -e

# Function to show usage
usage() {
    echo "----------------- box test -----------------"
    echo "Integration test suite and database management."
    echo ""
    echo "Usage: box test [options] <command>"
    echo ""
    echo "Options:"
    echo "    -h                  show this help"
    echo "    --master  N         number of masters  (1-2,  default: 1)"
    echo "    --player  N         number of players  (1-9,  default: 4)"
    echo "    --watcher N         number of watchers (0-5,  default: 0)"
    echo "    --name \"Room Name\"  room name (default: \"Integration Test Room\")"
    echo ""
    echo "Commands:"
    echo "    init            run full integration test"
    echo "    delete          flush Redis database (wipe all data)"
    echo ""
    echo "Examples:"
    echo "    box test init                                          # 1 master, 4 players"
    echo "    box test init --master 2 --player 3 --watcher 1        # custom composition"
    echo "    box test init --name \"My Room\" --player 6              # custom room name"
    echo "    box test delete                                        # clean Redis database"
    echo "    box -d test init                                       # run with debug output"
}

# Defaults
N_MASTERS=1
N_PLAYERS=4
N_WATCHERS=0
ROOM_NAME="Integration Test Room"

# Parse options (long options via while/case/shift)
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            usage && exit 0
            ;;
        --master)
            N_MASTERS="$2"
            if [[ -z "$N_MASTERS" || "$N_MASTERS" -lt 1 || "$N_MASTERS" -gt 2 ]] 2>/dev/null; then
                error "❌ --master must be between 1 and 2"
                exit 1
            fi
            shift 2
            ;;
        --player)
            N_PLAYERS="$2"
            if [[ -z "$N_PLAYERS" || "$N_PLAYERS" -lt 1 || "$N_PLAYERS" -gt 9 ]] 2>/dev/null; then
                error "❌ --player must be between 1 and 9"
                exit 1
            fi
            shift 2
            ;;
        --watcher)
            N_WATCHERS="$2"
            if [[ -z "$N_WATCHERS" || "$N_WATCHERS" -lt 0 || "$N_WATCHERS" -gt 5 ]] 2>/dev/null; then
                error "❌ --watcher must be between 0 and 5"
                exit 1
            fi
            shift 2
            ;;
        --name)
            ROOM_NAME="$2"
            if [[ -z "$ROOM_NAME" ]]; then
                error "❌ --name requires a value"
                exit 1
            fi
            shift 2
            ;;
        -*)
            error "❌ Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            # Positional argument (command)
            if [ -z "${COMMAND:-}" ]; then
                COMMAND="$1"
                shift
            else
                error "❌ Unexpected argument: $1"
                usage
                exit 1
            fi
            ;;
    esac
done

if [ -z "${COMMAND:-}" ]; then
    error "❌ No command specified"
    usage
    exit 1
fi

# Computed values
TOTAL_USERS=$((N_MASTERS + N_PLAYERS + N_WATCHERS))
N_ACTIVE=$((N_MASTERS + N_PLAYERS))  # Users who participate (send messages)

# Name pool (16 names, enough for max 2+9+5=16)
NAMES_POOL=(Alice Bob Charlie Diana Eve Frank Grace Henry Iris Jack Kate Leo Mia Noah Olivia Paul)

# Build dynamic NAMES and ROLES arrays
declare -a NAMES=()
declare -a ROLES=()
NAME_IDX=0

for ((i=0; i<N_MASTERS; i++)); do
    NAMES+=("${NAMES_POOL[$NAME_IDX]}")
    ROLES+=("master")
    NAME_IDX=$((NAME_IDX + 1))
done
for ((i=0; i<N_PLAYERS; i++)); do
    NAMES+=("${NAMES_POOL[$NAME_IDX]}")
    ROLES+=("player")
    NAME_IDX=$((NAME_IDX + 1))
done
for ((i=0; i<N_WATCHERS; i++)); do
    NAMES+=("${NAMES_POOL[$NAME_IDX]}")
    ROLES+=("watcher")
    NAME_IDX=$((NAME_IDX + 1))
done

# Test configuration
BASE_URL="https://${SUBDOMAIN}.${DOMAIN}"  # Public HTTPS route (HTTP redirects to HTTPS)
ADMIN_URL="http://localhost:8001"          # Will be accessed via SSH tunnel

# Function to set up SSH tunnel
setup_tunnel() {
    debug "🔗 Opening SSH tunnel to admin service..."
    ssh -f -N -i "${SSH_KEY}" -L 8001:localhost:8002 "${SSH_HOST}"
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
    info "Composition: $N_MASTERS master(s), $N_PLAYERS player(s), $N_WATCHERS watcher(s) ($TOTAL_USERS total)"

    check_services

    # Step 1: Create Room via Admin API
    debug "Step 1: Creating room..."

    ROOM_NAME_ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$ROOM_NAME'))")
    ROOM_RESPONSE=$(curl -s -X POST "$ADMIN_URL/admin/api/rooms?name=$ROOM_NAME_ENCODED")
    debug "Room response: $ROOM_RESPONSE"
    ROOM_ID=$(echo "$ROOM_RESPONSE" | jq -r 'keys[0]')

    if [[ "$ROOM_ID" == "null" || -z "$ROOM_ID" ]]; then
        error "Failed to create room. Response: $ROOM_RESPONSE"
        exit 1
    fi

    info "New room: $ROOM_ID ($ROOM_NAME)"

    # Step 2: Create users with codes via Admin API
    debug "Step 2: Creating $TOTAL_USERS users..."

    declare -a USER_IDS=()
    declare -a CODE_IDS=()

    for i in $(seq 0 $((TOTAL_USERS - 1))); do
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

    for i in $(seq 0 $((TOTAL_USERS - 1))); do
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
                "$BASE_URL/api/v1/rooms/$ROOM_ID/user/${USER_IDS[$i]}?next=$ROLE" 2>/dev/null)
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

    # Step 4b: Test card scoring
    debug "Step 4b: Testing card scoring..."

    # Get room state to find a card ID
    ROOM_STATE_FOR_SCORING=$(curl -s -L "$BASE_URL/api/v1/rooms/$ROOM_ID")
    FIRST_CARD_ID=$(echo "$ROOM_STATE_FOR_SCORING" | jq -r ".[\"$ROOM_ID\"].cards | keys[0]" 2>/dev/null || echo "")

    if [[ -n "$FIRST_CARD_ID" && "$FIRST_CARD_ID" != "null" ]]; then
        debug "Testing scoring with card: $FIRST_CARD_ID"

        # Test 1: Master assigns score to card (should succeed)
        MASTER_CODE=${CODE_IDS[0]}  # First user is master
        MASTER_SCORE_COOKIE="/tmp/master_score_cookie.txt"

        curl -s -L -c "$MASTER_SCORE_COOKIE" "$BASE_URL/r/$ROOM_ID?code_id=$MASTER_CODE" >/dev/null 2>&1

        if [ -f "$MASTER_SCORE_COOKIE" ] && [ -s "$MASTER_SCORE_COOKIE" ]; then
            MASTER_SCORE_RESPONSE=$(curl -s -L -b "$MASTER_SCORE_COOKIE" -X PATCH \
                -H "Content-Type: application/json" \
                -d '{"scored": 7}' \
                "$BASE_URL/api/v1/rooms/$ROOM_ID/cards/$FIRST_CARD_ID/score")

            info "Master score response: $MASTER_SCORE_RESPONSE"

            if [[ "$MASTER_SCORE_RESPONSE" == *"success"* ]]; then
                info "✓ Master successfully scored card"
                MASTER_SCORE_SUCCESS="true"
            else
                warning "✗ Master failed to score card"
                warning "Response was: $MASTER_SCORE_RESPONSE"
                MASTER_SCORE_SUCCESS="false"
            fi
        else
            error "Failed to authenticate master for scoring"
            MASTER_SCORE_SUCCESS="false"
        fi

        rm -f "$MASTER_SCORE_COOKIE"

        # Small delay between tests
        sleep 0.1

        # Test 2: Player tries to assign score to card (should fail)
        # Find first player index
        PLAYER_INDEX=-1
        for i in $(seq 0 $((TOTAL_USERS - 1))); do
            if [[ "${ROLES[$i]}" == "player" ]]; then
                PLAYER_INDEX=$i
                break
            fi
        done

        if [[ "$PLAYER_INDEX" -ge 0 ]]; then
            PLAYER_CODE=${CODE_IDS[$PLAYER_INDEX]}
            PLAYER_SCORE_COOKIE="/tmp/player_score_cookie.txt"

            curl -s -L -c "$PLAYER_SCORE_COOKIE" "$BASE_URL/r/$ROOM_ID?code_id=$PLAYER_CODE" >/dev/null 2>&1

            if [ -f "$PLAYER_SCORE_COOKIE" ] && [ -s "$PLAYER_SCORE_COOKIE" ]; then
                PLAYER_SCORE_RESPONSE=$(curl -s -L -b "$PLAYER_SCORE_COOKIE" -X PATCH \
                    -H "Content-Type: application/json" \
                    -d '{"scored": 5}' \
                    "$BASE_URL/api/v1/rooms/$ROOM_ID/cards/$FIRST_CARD_ID/score")

                debug "Player score response: $PLAYER_SCORE_RESPONSE"

                # Player should get 403 error (not authorized)
                if [[ "$PLAYER_SCORE_RESPONSE" == *"only masters can score cards"* ]]; then
                    info "✓ Player correctly denied permission to score"
                    PLAYER_SCORE_DENIED="true"
                else
                    warning "✗ Player was not denied permission (unexpected)"
                    PLAYER_SCORE_DENIED="false"
                fi
            else
                error "Failed to authenticate player for scoring test"
                PLAYER_SCORE_DENIED="false"
            fi

            rm -f "$PLAYER_SCORE_COOKIE"
        else
            warning "No players to test scoring denial"
            PLAYER_SCORE_DENIED="false"
        fi
    else
        warning "No cards found for scoring tests"
        MASTER_SCORE_SUCCESS="false"
        PLAYER_SCORE_DENIED="false"
    fi

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
        "The closest to the right order wins the round! Each player gets one card with a number from 1 to 10, and we have to arrange ourselves in order without showing our cards. It's all about strategy, communication, and a bit of luck!"
        "Can't wait to see my card! Let's do this 🎮"
        "Good luck everyone!"
        "May the best player win 🏆"
        "Let's goooo!"
    )

    # Build sender arrays: cycle through active users (masters + players, not watchers)
    declare -a MESSAGE_SENDERS=()
    declare -a SENDER_NAMES=()
    for i in {0..12}; do
        SENDER_INDEX=$((i % N_ACTIVE))
        MESSAGE_SENDERS[$i]=$SENDER_INDEX
        SENDER_NAMES[$i]=${NAMES[$SENDER_INDEX]}
    done

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
        sleep 0.1
    done

    # Step 5b: Test emoji reactions
    debug "Step 5b: Testing emoji reactions..."

    # Get room state to retrieve message IDs
    ROOM_STATE=$(curl -s "$BASE_URL/api/v1/rooms/$ROOM_ID")
    debug "Room state response: $ROOM_STATE"

    # Messages are stored as a dict/object with message IDs as keys
    # Convert to array of message objects for processing
    MESSAGES_JSON=$(echo "$ROOM_STATE" | jq ".[\"$ROOM_ID\"].messages // {} | to_entries | map(.value + {id: .key})")

    debug "Messages JSON: $MESSAGES_JSON"

    # Parse message IDs (now converted to array)
    declare -a MESSAGE_IDS
    MESSAGE_COUNT=$(echo "$MESSAGES_JSON" | jq 'length // 0')

    if [ "$MESSAGE_COUNT" -gt 0 ]; then
        info "Found $MESSAGE_COUNT messages, adding reactions..."

        # Extract message IDs into array
        for ((i=0; i<$MESSAGE_COUNT; i++)); do
            MSG_ID=$(echo "$MESSAGES_JSON" | jq -r ".[$i].id // \"null\"")
            MESSAGE_IDS[$i]=$MSG_ID
            debug "Message $i ID: $MSG_ID"
        done

        # Check if we got valid message IDs
        if [[ "${MESSAGE_IDS[0]}" == "null" || -z "${MESSAGE_IDS[0]}" ]]; then
            error "Failed to extract message IDs - messages might not have ID field"
            warning "Skipping reaction tests..."
        else

        # Define reactions: [message_index:user_index:emoji]
        # User indices are modulo-wrapped to stay within active user bounds
        declare -a REACTIONS=(
            "0:0:👍"
            "0:1:❤️"
            "3:2:😂"
            "3:3:🤩"
            "5:0:👎"
            "7:1:😬"
            "7:2:😂"
            "9:3:❤️"
            "11:0:🤩"
            "11:1:👍"
        )

        for reaction in "${REACTIONS[@]}"; do
            IFS=':' read -r MSG_INDEX RAW_USER_INDEX EMOJI <<< "$reaction"

            # Wrap user index to stay within active users
            USER_INDEX=$((RAW_USER_INDEX % N_ACTIVE))

            if [ $MSG_INDEX -lt $MESSAGE_COUNT ]; then
                MSG_ID=${MESSAGE_IDS[$MSG_INDEX]}
                USER_NAME=${NAMES[$USER_INDEX]}
                USER_CODE=${CODE_IDS[$USER_INDEX]}

                debug "Adding reaction $EMOJI from $USER_NAME to message $MSG_ID..."

                # Authenticate user and add reaction
                REACTOR_COOKIE="/tmp/reactor_${USER_INDEX}_cookie.txt"

                # Get authentication cookie
                curl -s -L -c "$REACTOR_COOKIE" "$BASE_URL/r/$ROOM_ID?code_id=$USER_CODE" >/dev/null 2>&1

                if [ -f "$REACTOR_COOKIE" ] && [ -s "$REACTOR_COOKIE" ]; then
                    # Add reaction using authenticated session
                    REACTION_RESPONSE=$(curl -s -L -b "$REACTOR_COOKIE" -X PATCH \
                        -H "Content-Type: application/json" \
                        -d "{\"emoji\": \"$EMOJI\", \"action\": \"add\"}" \
                        "$BASE_URL/api/v1/rooms/$ROOM_ID/messages/$MSG_ID/react")

                    debug "Reaction response: $REACTION_RESPONSE"

                    if [[ "$REACTION_RESPONSE" == *"success"* ]]; then
                        info "$USER_NAME reacted with $EMOJI to message #$MSG_INDEX"
                    else
                        error "Failed to add reaction from $USER_NAME: $REACTION_RESPONSE"
                    fi
                else
                    error "Failed to authenticate $USER_NAME for reaction"
                fi

                # Clean up reactor cookie
                rm -f "$REACTOR_COOKIE"

                # Small delay between reactions
                sleep 0.1
            fi
        done

        info "Emoji reactions test completed!"
        fi  # End of message ID validation check
    else
        warning "No messages found to add reactions to"
    fi

    # Step 6: Verify game state and messages
    debug "Step 6: Verifying final game state and messages..."

    # Get room details via ADMIN API to verify everything is set up correctly
    ADMIN_ALL_ROOMS=$(curl -s "$ADMIN_URL/admin/api/rooms")
    ADMIN_ROOM_STATE=$(echo "$ADMIN_ALL_ROOMS" | jq "{\"$ROOM_ID\": .[\"$ROOM_ID\"]}")

    debug "🔍 Raw admin room state:"
    debug "$(echo "$ADMIN_ROOM_STATE" | jq . 2>/dev/null || echo "$ADMIN_ROOM_STATE")"

    # Parse and validate the state using admin data (more reliable for user info)
    NUM_USERS=$(echo "$ADMIN_ROOM_STATE" | jq -r ".[\"$ROOM_ID\"].users | length" 2>/dev/null || echo "0")

    # Check cards/messages/round using public API (admin API doesn't include full game state)
    PUBLIC_ROOM_STATE=$(curl -s -L "$BASE_URL/api/v1/rooms/$ROOM_ID")

    # Round is now an object with {id, topic} properties
    ROUND_VALUE=$(echo "$PUBLIC_ROOM_STATE" | jq ".[\"$ROOM_ID\"].round" 2>/dev/null || echo "null")
    info "🔍 Round value: $ROUND_VALUE"
    ROUND_TYPE=$(echo "$ROUND_VALUE" | jq -r 'type' 2>/dev/null || echo 'unknown')
    info "🔍 Round type: $ROUND_TYPE"
    HAS_ROUND=$(echo "$PUBLIC_ROOM_STATE" | jq -r ".[\"$ROOM_ID\"].round | if type == \"object\" and .id != null then \"true\" else \"false\" end" 2>/dev/null || echo "false")
    info "🔍 HAS_ROUND result: $HAS_ROUND"

    HAS_CARDS=$(echo "$PUBLIC_ROOM_STATE" | jq -r ".[\"$ROOM_ID\"].cards | if type == \"object\" and length > 0 then \"true\" else \"false\" end" 2>/dev/null || echo "false")

    # Validate card data integrity (check if all cards have complete properties)
    CARD_INTEGRITY="true"
    CARD_DETAILS=""
    TOTAL_CARDS=0
    if [[ "$HAS_CARDS" == "true" ]]; then
        debug "🔍 Validating card data integrity..."

        # Extract all cards (object/dict with card_id as keys) and check their properties
        CARDS_JSON=$(echo "$PUBLIC_ROOM_STATE" | jq -r ".[\"$ROOM_ID\"].cards")
        TOTAL_CARDS=$(echo "$CARDS_JSON" | jq 'length' 2>/dev/null || echo "0")

        COMPLETE_CARDS=0

        if [[ "$TOTAL_CARDS" -gt 0 ]]; then
            # Iterate through object keys (card IDs)
            for CARD_ID in $(echo "$CARDS_JSON" | jq -r 'keys[]'); do
                # Check if card has all 4 required properties with valid values (flipped, value, player_id, peeked)
                CARD_DATA=$(echo "$CARDS_JSON" | jq -r ".\"$CARD_ID\"")

                FLIPPED=$(echo "$CARD_DATA" | jq -r '.flipped // empty')
                VALUE=$(echo "$CARD_DATA" | jq -r '.value // empty')
                PLAYER_ID=$(echo "$CARD_DATA" | jq -r '.player_id // empty')
                PEEKED=$(echo "$CARD_DATA" | jq -r '.peeked // empty')

                PROPS=0
                [[ -n "$FLIPPED" && "$FLIPPED" != "null" ]] && PROPS=$((PROPS + 1))
                [[ -n "$VALUE" && "$VALUE" != "null" ]] && PROPS=$((PROPS + 1))
                [[ -n "$PLAYER_ID" && "$PLAYER_ID" != "null" ]] && PROPS=$((PROPS + 1))
                [[ -n "$PEEKED" && "$PEEKED" != "null" ]] && PROPS=$((PROPS + 1))

                if [[ "$PROPS" == "4" ]]; then
                    COMPLETE_CARDS=$((COMPLETE_CARDS + 1))
                    debug "Card $CARD_ID: complete (4/4 properties)"
                else
                    debug "Card $CARD_ID: incomplete ($PROPS/4 properties)"
                    CARD_INTEGRITY="false"
                fi
            done
        fi

        CARD_DETAILS="$COMPLETE_CARDS/$TOTAL_CARDS"
        debug "Card integrity check: $COMPLETE_CARDS complete cards out of $TOTAL_CARDS total"
    fi

    # Verify user roles are correctly assigned
    declare -a ACTUAL_ROLES=()
    for i in $(seq 0 $((TOTAL_USERS - 1))); do
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

    # Get messages from public API (stored as dict/object with message IDs as keys)
    ROOM_MESSAGES_STRING=$(echo "$PUBLIC_ROOM_STATE" | jq -r ".[\"$ROOM_ID\"].messages // {} | to_entries | map(.value + {id: .key})" 2>/dev/null || echo "[]")

    if [[ "$ROOM_MESSAGES_STRING" != "null" && "$ROOM_MESSAGES_STRING" != "" && "$ROOM_MESSAGES_STRING" != "[]" ]]; then
        ROOM_MESSAGES="$ROOM_MESSAGES_STRING"

        MESSAGE_COUNT=$(echo "$ROOM_MESSAGES" | jq 'length' 2>/dev/null || echo "0")

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
    TOTAL_ASSERTIONS=11

    # Assertion 1: Room exists and accessible
    if [[ "$ROOM_ID" != "null" && -n "$ROOM_ID" ]]; then
        success "Room creation: ok"
        ASSERTIONS_PASSED=$((ASSERTIONS_PASSED + 1))
    else
        error "Room creation: failed"
    fi

    # Assertion 2: All users joined room
    if [[ "$NUM_USERS" == "$TOTAL_USERS" ]]; then
        success "Users in room: ok ($NUM_USERS/$TOTAL_USERS)"
        ASSERTIONS_PASSED=$((ASSERTIONS_PASSED + 1))
    else
        error "Users in room: failed ($NUM_USERS/$TOTAL_USERS)"
    fi

    # Assertion 3: All user roles correctly assigned
    CORRECT_ROLES=0
    for i in $(seq 0 $((TOTAL_USERS - 1))); do
        if [[ "${ACTUAL_ROLES[$i]}" == "${ROLES[$i]}" ]]; then
            CORRECT_ROLES=$((CORRECT_ROLES + 1))
        fi
    done

    if [[ "$CORRECT_ROLES" == "$TOTAL_USERS" ]]; then
        success "User roles: ok ($CORRECT_ROLES/$TOTAL_USERS)"
        ASSERTIONS_PASSED=$((ASSERTIONS_PASSED + 1))
    else
        error "User roles: failed ($CORRECT_ROLES/$TOTAL_USERS)"
    fi

    # Assertion 4: Round created
    if [[ "$HAS_ROUND" == "true" ]]; then
        success "Round creation: ok"
        ASSERTIONS_PASSED=$((ASSERTIONS_PASSED + 1))
    else
        error "Round creation: failed"
    fi

    # Assertion 5: Cards distributed (one per player)
    if [[ "$HAS_CARDS" == "true" && "$TOTAL_CARDS" == "$N_PLAYERS" ]]; then
        success "Cards distribution: ok ($TOTAL_CARDS cards for $N_PLAYERS players)"
        ASSERTIONS_PASSED=$((ASSERTIONS_PASSED + 1))
    elif [[ "$HAS_CARDS" == "true" ]]; then
        error "Cards distribution: wrong count ($TOTAL_CARDS cards for $N_PLAYERS players)"
    else
        error "Cards distribution: failed"
    fi

    # Assertion 6: Card data integrity (detects corruption)
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

    # Assertion 9: Emoji reactions added
    MESSAGES_WITH_REACTIONS=0
    TOTAL_REACTIONS=0

    if [[ "$ROOM_MESSAGES" != "null" && "$ROOM_MESSAGES" != "" && "$ROOM_MESSAGES" != "[]" ]]; then
        debug "Checking reactions in $MESSAGE_COUNT messages..."
        for i in $(seq 0 $((MESSAGE_COUNT - 1))); do
            HAS_REACTIONS=$(echo "$ROOM_MESSAGES" | jq -r ".[$i].reactions | if type == \"object\" and length > 0 then \"true\" else \"false\" end" 2>/dev/null || echo "false")
            if [[ "$HAS_REACTIONS" == "true" ]]; then
                MESSAGES_WITH_REACTIONS=$((MESSAGES_WITH_REACTIONS + 1))
                REACTION_COUNT=$(echo "$ROOM_MESSAGES" | jq -r ".[$i].reactions | to_entries | map(.value | length) | add" 2>/dev/null || echo "0")
                TOTAL_REACTIONS=$((TOTAL_REACTIONS + REACTION_COUNT))
                debug "Message $i has $REACTION_COUNT reactions"
            fi
        done
        debug "Total: $TOTAL_REACTIONS reactions across $MESSAGES_WITH_REACTIONS messages"
    else
        debug "No messages available for reaction validation"
    fi

    if [[ "$MESSAGES_WITH_REACTIONS" -ge 5 && "$TOTAL_REACTIONS" -ge 10 ]]; then
        success "Emoji reactions: ok ($TOTAL_REACTIONS reactions on $MESSAGES_WITH_REACTIONS messages)"
        ASSERTIONS_PASSED=$((ASSERTIONS_PASSED + 1))
    else
        error "Emoji reactions: failed ($TOTAL_REACTIONS reactions on $MESSAGES_WITH_REACTIONS messages, expected 10+ on 5+ messages)"
    fi

    # Assertion 10: Master can score cards
    CARD_SCORE=""
    if [[ -n "$FIRST_CARD_ID" && "$FIRST_CARD_ID" != "null" ]]; then
        CARD_SCORE=$(echo "$PUBLIC_ROOM_STATE" | jq -r ".[\"$ROOM_ID\"].cards[\"$FIRST_CARD_ID\"].scored" 2>/dev/null || echo "null")
        debug "Card score in state: $CARD_SCORE"
    fi

    if [[ "$MASTER_SCORE_SUCCESS" == "true" && "$CARD_SCORE" == "7" ]]; then
        success "Master card scoring: ok (score=7 confirmed)"
        ASSERTIONS_PASSED=$((ASSERTIONS_PASSED + 1))
    else
        error "Master card scoring: failed (success=$MASTER_SCORE_SUCCESS, score=$CARD_SCORE)"
    fi

    # Assertion 11: Player cannot score cards (denied)
    if [[ "$PLAYER_SCORE_DENIED" == "true" ]]; then
        success "Player scoring denial: ok (permission correctly denied)"
        ASSERTIONS_PASSED=$((ASSERTIONS_PASSED + 1))
    else
        error "Player scoring denial: failed (player was not denied permission)"
    fi

    # Overall test result
    if [[ "$ASSERTIONS_PASSED" == "$TOTAL_ASSERTIONS" ]]; then
        success "🎉 Integration test PASSED ($ASSERTIONS_PASSED/$TOTAL_ASSERTIONS assertions)"

        info "Test room ready for manual testing!"

        # Show URLs for each created user
        for i in $(seq 0 $((TOTAL_USERS - 1))); do
            USER_NAME=${NAMES[$i]}
            CODE_ID=${CODE_IDS[$i]}
            ROLE=${ROLES[$i]}
            USER_URL="$BASE_URL/r/$ROOM_ID?code_id=$CODE_ID"
            info "$USER_NAME ($ROLE): $USER_URL"
        done

        info "Use 'box test delete' to clean Redis when you're done testing"

        exit 0
    else
        error "❌ Integration test FAILED ($ASSERTIONS_PASSED/$TOTAL_ASSERTIONS assertions passed)"

        debug "🔍 Admin room state debug:"
        debug "$(echo "$ADMIN_ROOM_STATE" | jq . 2>/dev/null || echo "$ADMIN_ROOM_STATE")"

        info "Test room preserved for debugging!"
        info "Use 'box test delete' to clean Redis when you're done debugging"

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
