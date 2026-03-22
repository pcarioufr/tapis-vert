#!/bin/bash

# Tapis Vert Integration Test Suite
# Tests room creation, user management, roles, permissions, and round logic via public APIs
#
# Fixed composition: 2 masters, 5 players, 5 watchers (12 users)
# Runs two rounds to validate the next→role promotion system

set -e

# Function to show usage
usage() {
    echo "----------------- box test -----------------"
    echo "Integration test suite and database management."
    echo ""
    echo "Usage: box test <command>"
    echo ""
    echo "Options:"
    echo "    -h              show this help"
    echo ""
    echo "Commands:"
    echo "    init            run full integration test"
    echo "    delete          flush Redis database (wipe all data)"
    echo ""
    echo "Composition: 2 masters, 5 players, 5 watchers (12 users)"
    echo ""
    echo "Examples:"
    echo "    box test init                  # run full test suite"
    echo "    box test delete                # clean Redis database"
    echo "    box -d test init               # run with debug output"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            usage && exit 0
            ;;
        -*)
            error "Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            if [ -z "${COMMAND:-}" ]; then
                COMMAND="$1"
                shift
            else
                error "Unexpected argument: $1"
                usage
                exit 1
            fi
            ;;
    esac
done

if [ -z "${COMMAND:-}" ]; then
    error "No command specified"
    usage
    exit 1
fi

# Fixed composition
NAMES=(Alice Bob Charlie Diana Eve Frank Grace Henry Iris Jack Kate Leo)
ROLES=(master master player player player player player watcher watcher watcher watcher watcher)
TOTAL_USERS=12
N_MASTERS=2
N_PLAYERS=5
N_WATCHERS=5
N_ACTIVE=7  # masters + players (can send messages)

# Test configuration
BASE_URL="https://${SUBDOMAIN}.${DOMAIN}"
ADMIN_URL="http://localhost:8001"

# --- Helper functions ---

setup_tunnel() {
    debug "Opening SSH tunnel to admin service..."
    ssh -f -N -i "${SSH_KEY}" -L 8001:localhost:8002 "${SSH_HOST}"
    debug "Admin service tunnel established"
}

cleanup_tunnel() {
    pkill -f "ssh.*-L.*8001:localhost:8002" 2>/dev/null || true
}

check_services() {
    debug "Checking if services are accessible..."
    if ! curl -s -L "$BASE_URL/ping" > /dev/null 2>&1; then
        error "Public webapp not accessible at $BASE_URL"
        exit 1
    fi
    if ! curl -s "$ADMIN_URL/admin/ping" > /dev/null 2>&1; then
        error "Admin webapp not accessible at $ADMIN_URL (via SSH tunnel)"
        exit 1
    fi
    debug "Services accessible"
}

# Authenticate a user and store cookie at /tmp/cookie_<index>.txt
# Usage: auth_user <index>
auth_user() {
    local idx=$1
    local cookie="/tmp/cookie_${idx}.txt"
    curl -s -L -c "$cookie" "$BASE_URL/r/$ROOM_ID?code_id=${CODE_IDS[$idx]}" >/dev/null 2>&1
    if [ ! -f "$cookie" ] || [ ! -s "$cookie" ]; then
        error "Failed to authenticate ${NAMES[$idx]}"
        return 1
    fi
    echo "$cookie"
}

# Make an authenticated API call
# Usage: api_call <index> <method> <path> [curl_extra_args...]
api_call() {
    local idx=$1; shift
    local method=$1; shift
    local path=$1; shift
    local cookie
    cookie=$(auth_user "$idx") || return 1
    local response
    response=$(curl -s -L -b "$cookie" -X "$method" "$@" "$BASE_URL$path" 2>/dev/null)
    rm -f "$cookie"
    echo "$response"
}

# Check if an API response indicates an error (contains "error" key or HTML)
# Usage: is_error <response>
is_error() {
    [[ "$1" == *"401 Unauthorized"* || "$1" == *"html"* || "$1" == *"\"error\""* ]]
}

# Assert helper: increments PASS counter and logs result
# Usage: assert <description> <condition_result (true/false)>
assert() {
    local desc=$1
    local result=$2
    TOTAL_ASSERTIONS=$((TOTAL_ASSERTIONS + 1))
    if [[ "$result" == "true" ]]; then
        success "$desc: ok"
        ASSERTIONS_PASSED=$((ASSERTIONS_PASSED + 1))
    else
        error "$desc: failed"
    fi
}

# --- Main test function ---

test_init() {

    notice "Starting Tapis Vert Integration Test..."
    info "Composition: $N_MASTERS masters, $N_PLAYERS players, $N_WATCHERS watchers ($TOTAL_USERS total)"

    check_services

    ASSERTIONS_PASSED=0
    TOTAL_ASSERTIONS=0

    # =========================================================================
    # STEP 1: Create room
    # =========================================================================
    debug "Step 1: Creating room..."

    ROOM_RESPONSE=$(curl -s -X POST "$ADMIN_URL/admin/api/rooms?name=Integration%20Test%20Room")
    ROOM_ID=$(echo "$ROOM_RESPONSE" | jq -r 'keys[0]')

    if [[ "$ROOM_ID" == "null" || -z "$ROOM_ID" ]]; then
        error "Failed to create room"
        exit 1
    fi
    info "Room created: $ROOM_ID"

    # =========================================================================
    # STEP 2: Create users
    # =========================================================================
    debug "Step 2: Creating $TOTAL_USERS users..."

    declare -a USER_IDS=()
    declare -a CODE_IDS=()

    for i in $(seq 0 $((TOTAL_USERS - 1))); do
        USER_RESPONSE=$(curl -s -X POST "$ADMIN_URL/admin/api/users?name=${NAMES[$i]}")
        USER_ID=$(echo "$USER_RESPONSE" | jq -r 'keys[0]' 2>/dev/null)
        CODE_ID=$(echo "$USER_RESPONSE" | jq -r ".[\"$USER_ID\"].codes | keys[0]" 2>/dev/null)

        if [[ "$USER_ID" == "null" || -z "$USER_ID" || "$CODE_ID" == "null" || -z "$CODE_ID" ]]; then
            error "Failed to create user ${NAMES[$i]}"
            exit 1
        fi

        USER_IDS[$i]=$USER_ID
        CODE_IDS[$i]=$CODE_ID
        info "User ${NAMES[$i]}: $USER_ID (${ROLES[$i]})"
    done

    # =========================================================================
    # STEP 3: Join room and set next roles
    # =========================================================================
    debug "Step 3: Joining users to room and setting next roles..."

    for i in $(seq 0 $((TOTAL_USERS - 1))); do
        # Authenticate
        local cookie
        cookie=$(auth_user "$i") || continue

        # Join room (default: watcher)
        curl -s -L -b "$cookie" -X POST "$BASE_URL/api/v1/rooms/$ROOM_ID/join" >/dev/null 2>&1

        # Set next role
        curl -s -L -b "$cookie" -X PATCH "$BASE_URL/api/v1/rooms/$ROOM_ID/user/${USER_IDS[$i]}?next=${ROLES[$i]}" >/dev/null 2>&1

        rm -f "$cookie"
        info "${NAMES[$i]} joined, next=${ROLES[$i]}"
    done

    # =========================================================================
    # STEP 4: Start round 1 via admin API (promotes next→role)
    # =========================================================================
    debug "Step 4: Starting round 1 (via admin)..."

    # Use admin API for first round — all users join as watcher, so nobody
    # has the role to start a round via the public API yet
    ROUND_RESPONSE=$(curl -s -X POST "$ADMIN_URL/admin/api/rooms/$ROOM_ID/round")
    debug "Round 1 response: $ROUND_RESPONSE"
    info "Round 1 started"

    # Get room state after round
    ROOM_STATE=$(curl -s -L "$BASE_URL/api/v1/rooms/$ROOM_ID")
    ADMIN_STATE=$(curl -s "$ADMIN_URL/admin/api/rooms" | jq "{\"$ROOM_ID\": .[\"$ROOM_ID\"]}")

    # =========================================================================
    # STEP 5: Verify round 1 state
    # =========================================================================
    debug "Step 5: Verifying round 1 state..."

    # 5a: Room exists
    assert "Room creation" "$([[ "$ROOM_ID" != "null" && -n "$ROOM_ID" ]] && echo true || echo false)"

    # 5b: All users joined
    NUM_USERS=$(echo "$ADMIN_STATE" | jq -r ".[\"$ROOM_ID\"].users | length" 2>/dev/null || echo "0")
    assert "Users in room ($NUM_USERS/$TOTAL_USERS)" "$([[ "$NUM_USERS" == "$TOTAL_USERS" ]] && echo true || echo false)"

    # 5c: Roles correctly promoted (next→role)
    CORRECT_ROLES=0
    for i in $(seq 0 $((TOTAL_USERS - 1))); do
        ACTUAL_ROLE=$(echo "$ADMIN_STATE" | jq -r ".[\"$ROOM_ID\"].users.\"${USER_IDS[$i]}\".relation.role" 2>/dev/null)
        if [[ "$ACTUAL_ROLE" == "${ROLES[$i]}" ]]; then
            CORRECT_ROLES=$((CORRECT_ROLES + 1))
            debug "${NAMES[$i]}: role=$ACTUAL_ROLE (ok)"
        else
            error "${NAMES[$i]}: expected ${ROLES[$i]}, got $ACTUAL_ROLE"
        fi
    done
    assert "Round 1 roles ($CORRECT_ROLES/$TOTAL_USERS)" "$([[ "$CORRECT_ROLES" == "$TOTAL_USERS" ]] && echo true || echo false)"

    # 5d: Round exists
    HAS_ROUND=$(echo "$ROOM_STATE" | jq -r ".[\"$ROOM_ID\"].round | if type == \"object\" and .id != null then \"true\" else \"false\" end" 2>/dev/null || echo "false")
    assert "Round 1 created" "$HAS_ROUND"

    # 5e: Cards distributed (one per player = 5)
    TOTAL_CARDS=$(echo "$ROOM_STATE" | jq -r ".[\"$ROOM_ID\"].cards | length" 2>/dev/null || echo "0")
    assert "Round 1 cards ($TOTAL_CARDS/$N_PLAYERS)" "$([[ "$TOTAL_CARDS" == "$N_PLAYERS" ]] && echo true || echo false)"

    # 5f: Card data integrity
    CARDS_JSON=$(echo "$ROOM_STATE" | jq ".[\"$ROOM_ID\"].cards // {}")
    COMPLETE_CARDS=0
    for CARD_ID in $(echo "$CARDS_JSON" | jq -r 'keys[]' 2>/dev/null); do
        PROPS=$(echo "$CARDS_JSON" | jq "[.\"$CARD_ID\" | .flipped, .value, .player_id, .peeked | select(. != null)] | length" 2>/dev/null || echo "0")
        [[ "$PROPS" == "4" ]] && COMPLETE_CARDS=$((COMPLETE_CARDS + 1))
    done
    assert "Card integrity ($COMPLETE_CARDS/$TOTAL_CARDS)" "$([[ "$COMPLETE_CARDS" == "$TOTAL_CARDS" && "$TOTAL_CARDS" -gt 0 ]] && echo true || echo false)"

    # =========================================================================
    # STEP 6: Test permissions (round 1)
    # =========================================================================
    debug "Step 6: Testing permissions..."

    # Find card IDs and their owners for permission tests
    FIRST_CARD_ID=$(echo "$CARDS_JSON" | jq -r 'keys[0]' 2>/dev/null)
    FIRST_CARD_OWNER=$(echo "$CARDS_JSON" | jq -r ".\"$FIRST_CARD_ID\".player_id" 2>/dev/null)

    # Find indices by role for targeted tests
    MASTER_IDX=0    # Alice (master)
    PLAYER_IDX=2    # Charlie (player)
    WATCHER_IDX=7   # Henry (watcher)

    # Find a player who does NOT own the first card (for flip denial test)
    OTHER_PLAYER_IDX=-1
    for i in 2 3 4 5 6; do
        if [[ "${USER_IDS[$i]}" != "$FIRST_CARD_OWNER" ]]; then
            OTHER_PLAYER_IDX=$i
            break
        fi
    done

    # 6a: Master can score a card
    SCORE_RESP=$(api_call $MASTER_IDX PATCH "/api/v1/rooms/$ROOM_ID/cards/$FIRST_CARD_ID/score" \
        -H "Content-Type: application/json" -d '{"scored": 7}')
    assert "Master can score card" "$([[ "$SCORE_RESP" == *"success"* ]] && echo true || echo false)"

    sleep 0.1

    # 6b: Player cannot score a card
    SCORE_RESP=$(api_call $PLAYER_IDX PATCH "/api/v1/rooms/$ROOM_ID/cards/$FIRST_CARD_ID/score" \
        -H "Content-Type: application/json" -d '{"scored": 5}')
    assert "Player denied scoring" "$([[ "$SCORE_RESP" == *"only masters can score"* ]] && echo true || echo false)"

    sleep 0.1

    # 6c: Player cannot flip another player's card
    if [[ "$OTHER_PLAYER_IDX" -ge 0 ]]; then
        FLIP_RESP=$(api_call $OTHER_PLAYER_IDX PATCH "/api/v1/rooms/$ROOM_ID?cards:${FIRST_CARD_ID}:flipped=True")
        # Should get 403 (empty JSON response from flask.jsonify())
        assert "Player denied flipping other's card" "$([[ "$FLIP_RESP" == "{}" || "$FLIP_RESP" == "null" || -z "$FLIP_RESP" ]] && echo true || echo false)"
    else
        assert "Player denied flipping other's card" "false"
    fi

    sleep 0.1

    # 6d: Master cannot peek a card
    PEEK_RESP=$(api_call $MASTER_IDX PATCH "/api/v1/rooms/$ROOM_ID?cards:${FIRST_CARD_ID}:peeked:${USER_IDS[$MASTER_IDX]}=True")
    assert "Master denied peeking card" "$([[ "$PEEK_RESP" == "{}" || "$PEEK_RESP" == "null" || -z "$PEEK_RESP" ]] && echo true || echo false)"

    sleep 0.1

    # 6e: Watcher cannot send a message
    WATCHER_MSG_RESP=$(api_call $WATCHER_IDX POST "/api/v1/rooms/$ROOM_ID/message" \
        -H "Content-Type: application/json" -d '{"content": "I should not be able to send this"}')
    assert "Watcher denied messaging" "$([[ "$WATCHER_MSG_RESP" == *"watchers cannot send messages"* ]] && echo true || echo false)"

    sleep 0.1

    # 6f: Watcher cannot start a new round
    WATCHER_ROUND_RESP=$(api_call $WATCHER_IDX POST "/api/v1/rooms/$ROOM_ID/round")
    assert "Watcher denied starting round" "$([[ "$WATCHER_ROUND_RESP" == *"watchers cannot start"* ]] && echo true || echo false)"

    # =========================================================================
    # STEP 7: Messaging (masters and players send, watchers cannot)
    # =========================================================================
    debug "Step 7: Sending messages..."

    declare -a TEST_MESSAGES=(
        "Hello"
        "Salut, comment ça va"
        "Yay!!!!!!!"
        "Hey everyone! Ready to play?"
        "I'm so ready! This is going to be fun"
        "Count me in!"
        "Top 10! We each get a card and try to guess the order"
        "Ooh sounds interesting! How do we win?"
        "The closest to the right order wins the round!"
        "Let's do this"
        "Good luck everyone!"
        "May the best player win"
        "Let's goooo!"
    )

    # Cycle senders through active users (indices 0-6: masters + players)
    declare -a MESSAGE_SENDERS=()
    for i in {0..12}; do
        MESSAGE_SENDERS[$i]=$((i % N_ACTIVE))
    done

    for i in {0..12}; do
        SENDER_IDX=${MESSAGE_SENDERS[$i]}
        RESP=$(api_call $SENDER_IDX POST "/api/v1/rooms/$ROOM_ID/message" \
            -H "Content-Type: application/json" -d "{\"content\": \"${TEST_MESSAGES[$i]}\"}")
        if is_error "$RESP"; then
            error "Failed to send message from ${NAMES[$SENDER_IDX]}"
        else
            debug "${NAMES[$SENDER_IDX]} sent: '${TEST_MESSAGES[$i]}'"
        fi
        sleep 0.1
    done

    info "13 messages sent"

    # =========================================================================
    # STEP 8: Emoji reactions (including watcher reactions)
    # =========================================================================
    debug "Step 8: Adding emoji reactions..."

    # Fetch message IDs
    ROOM_STATE=$(curl -s -L "$BASE_URL/api/v1/rooms/$ROOM_ID")
    MESSAGES_JSON=$(echo "$ROOM_STATE" | jq ".[\"$ROOM_ID\"].messages // {}")
    MESSAGE_COUNT=$(echo "$MESSAGES_JSON" | jq 'length' 2>/dev/null || echo "0")

    declare -a MESSAGE_IDS=()
    MSG_IDX=0
    for KEY in $(echo "$MESSAGES_JSON" | jq -r 'keys[]' 2>/dev/null); do
        MESSAGE_IDS[$MSG_IDX]=$KEY
        MSG_IDX=$((MSG_IDX + 1))
    done

    info "Found $MESSAGE_COUNT messages"

    if [[ "$MESSAGE_COUNT" -gt 0 && "${MESSAGE_IDS[0]}" != "null" ]]; then
        # Reactions: msg_index:user_index:emoji
        # Includes watchers (indices 7-11) to verify they CAN react
        declare -a REACTIONS=(
            "0:0:👍"       # Alice (master)
            "0:2:❤️"       # Charlie (player)
            "0:7:😂"       # Henry (watcher) — watchers can react
            "3:3:🤩"       # Diana (player)
            "3:8:👍"       # Iris (watcher)
            "5:1:👎"       # Bob (master)
            "7:4:😬"       # Eve (player)
            "7:9:❤️"       # Jack (watcher)
            "9:5:😂"       # Frank (player)
            "11:10:🤩"     # Kate (watcher)
            "11:6:👍"      # Grace (player)
            "11:11:❤️"     # Leo (watcher)
        )

        WATCHER_REACTION_OK="false"

        for reaction in "${REACTIONS[@]}"; do
            IFS=':' read -r MSG_I USER_I EMOJI <<< "$reaction"
            if [[ $MSG_I -lt $MESSAGE_COUNT ]]; then
                MSG_ID=${MESSAGE_IDS[$MSG_I]}
                RESP=$(api_call $USER_I PATCH "/api/v1/rooms/$ROOM_ID/messages/$MSG_ID/react" \
                    -H "Content-Type: application/json" -d "{\"emoji\": \"$EMOJI\", \"action\": \"add\"}")
                if [[ "$RESP" == *"success"* ]]; then
                    debug "${NAMES[$USER_I]} reacted $EMOJI to message #$MSG_I"
                    # Track if a watcher reaction succeeded (user index 7-11)
                    if [[ $USER_I -ge 7 ]]; then
                        WATCHER_REACTION_OK="true"
                    fi
                else
                    error "Reaction failed from ${NAMES[$USER_I]}: $RESP"
                fi
            fi
            sleep 0.1
        done

        info "Reactions added"
    else
        WATCHER_REACTION_OK="false"
    fi

    # 8a: Watcher can react to messages
    assert "Watcher can react to messages" "$WATCHER_REACTION_OK"

    # =========================================================================
    # STEP 9: Verify messages and reactions
    # =========================================================================
    debug "Step 9: Verifying messages and reactions..."

    # Re-fetch state for verification
    ROOM_STATE=$(curl -s -L "$BASE_URL/api/v1/rooms/$ROOM_ID")
    ROOM_MESSAGES=$(echo "$ROOM_STATE" | jq ".[\"$ROOM_ID\"].messages // {} | to_entries | map(.value + {id: .key})")
    FINAL_MSG_COUNT=$(echo "$ROOM_MESSAGES" | jq 'length' 2>/dev/null || echo "0")

    # Verify message count
    assert "Message count ($FINAL_MSG_COUNT/13)" "$([[ "$FINAL_MSG_COUNT" == "13" ]] && echo true || echo false)"

    # Verify message content
    CORRECT_MESSAGES=0
    for i in {0..12}; do
        SENDER_IDX=${MESSAGE_SENDERS[$i]}
        EXPECTED_AUTHOR=${USER_IDS[$SENDER_IDX]}
        FOUND=$(echo "$ROOM_MESSAGES" | jq -r "map(select(.content == \"${TEST_MESSAGES[$i]}\" and .author == \"$EXPECTED_AUTHOR\")) | length" 2>/dev/null || echo "0")
        if [[ "$FOUND" == "1" ]]; then
            CORRECT_MESSAGES=$((CORRECT_MESSAGES + 1))
        else
            error "Missing: '${TEST_MESSAGES[$i]}' from ${NAMES[$SENDER_IDX]}"
        fi
    done
    assert "Message content ($CORRECT_MESSAGES/13)" "$([[ "$CORRECT_MESSAGES" == "13" ]] && echo true || echo false)"

    # Verify reactions
    TOTAL_REACTIONS=0
    MESSAGES_WITH_REACTIONS=0
    for i in $(seq 0 $((FINAL_MSG_COUNT - 1))); do
        HAS_R=$(echo "$ROOM_MESSAGES" | jq -r ".[$i].reactions | if type == \"object\" and length > 0 then \"true\" else \"false\" end" 2>/dev/null || echo "false")
        if [[ "$HAS_R" == "true" ]]; then
            MESSAGES_WITH_REACTIONS=$((MESSAGES_WITH_REACTIONS + 1))
            R_COUNT=$(echo "$ROOM_MESSAGES" | jq -r ".[$i].reactions | to_entries | map(.value | length) | add" 2>/dev/null || echo "0")
            TOTAL_REACTIONS=$((TOTAL_REACTIONS + R_COUNT))
        fi
    done
    assert "Emoji reactions ($TOTAL_REACTIONS reactions on $MESSAGES_WITH_REACTIONS messages)" \
        "$([[ "$TOTAL_REACTIONS" -ge 12 && "$MESSAGES_WITH_REACTIONS" -ge 5 ]] && echo true || echo false)"

    # Verify score persisted
    CARD_SCORE=$(echo "$ROOM_STATE" | jq -r ".[\"$ROOM_ID\"].cards.\"$FIRST_CARD_ID\".scored" 2>/dev/null || echo "null")
    assert "Card score persisted (=$CARD_SCORE)" "$([[ "$CARD_SCORE" == "7" ]] && echo true || echo false)"

    # =========================================================================
    # STEP 10: Role swaps via next (before round 2)
    # =========================================================================
    debug "Step 10: Swapping roles for round 2..."

    # Swap 3 users:
    #   Henry  (index 7):  watcher → player
    #   Charlie (index 2): player  → master
    #   Alice  (index 0):  master  → watcher
    SWAP_HENRY=$(api_call 7 PATCH "/api/v1/rooms/$ROOM_ID/user/${USER_IDS[7]}?next=player")
    SWAP_CHARLIE=$(api_call 2 PATCH "/api/v1/rooms/$ROOM_ID/user/${USER_IDS[2]}?next=master")
    SWAP_ALICE=$(api_call 0 PATCH "/api/v1/rooms/$ROOM_ID/user/${USER_IDS[0]}?next=watcher")

    info "Role swaps queued: Henry→player, Charlie→master, Alice→watcher"

    # Verify next is set but role is unchanged (two-phase check)
    ADMIN_STATE=$(curl -s "$ADMIN_URL/admin/api/rooms" | jq "{\"$ROOM_ID\": .[\"$ROOM_ID\"]}")

    HENRY_ROLE_BEFORE=$(echo "$ADMIN_STATE" | jq -r ".[\"$ROOM_ID\"].users.\"${USER_IDS[7]}\".relation.role" 2>/dev/null)
    HENRY_NEXT_BEFORE=$(echo "$ADMIN_STATE" | jq -r ".[\"$ROOM_ID\"].users.\"${USER_IDS[7]}\".relation.next" 2>/dev/null)
    CHARLIE_ROLE_BEFORE=$(echo "$ADMIN_STATE" | jq -r ".[\"$ROOM_ID\"].users.\"${USER_IDS[2]}\".relation.role" 2>/dev/null)
    CHARLIE_NEXT_BEFORE=$(echo "$ADMIN_STATE" | jq -r ".[\"$ROOM_ID\"].users.\"${USER_IDS[2]}\".relation.next" 2>/dev/null)
    ALICE_ROLE_BEFORE=$(echo "$ADMIN_STATE" | jq -r ".[\"$ROOM_ID\"].users.\"${USER_IDS[0]}\".relation.role" 2>/dev/null)
    ALICE_NEXT_BEFORE=$(echo "$ADMIN_STATE" | jq -r ".[\"$ROOM_ID\"].users.\"${USER_IDS[0]}\".relation.next" 2>/dev/null)

    debug "Before round 2: Henry role=$HENRY_ROLE_BEFORE next=$HENRY_NEXT_BEFORE"
    debug "Before round 2: Charlie role=$CHARLIE_ROLE_BEFORE next=$CHARLIE_NEXT_BEFORE"
    debug "Before round 2: Alice role=$ALICE_ROLE_BEFORE next=$ALICE_NEXT_BEFORE"

    # Role should still be the round 1 role, next should be the new value
    TWO_PHASE_OK="true"
    [[ "$HENRY_ROLE_BEFORE" != "watcher" ]] && TWO_PHASE_OK="false"
    [[ "$HENRY_NEXT_BEFORE" != "player" ]] && TWO_PHASE_OK="false"
    [[ "$CHARLIE_ROLE_BEFORE" != "player" ]] && TWO_PHASE_OK="false"
    [[ "$CHARLIE_NEXT_BEFORE" != "master" ]] && TWO_PHASE_OK="false"
    [[ "$ALICE_ROLE_BEFORE" != "master" ]] && TWO_PHASE_OK="false"
    [[ "$ALICE_NEXT_BEFORE" != "watcher" ]] && TWO_PHASE_OK="false"

    assert "Two-phase: next set but role unchanged" "$TWO_PHASE_OK"

    # =========================================================================
    # STEP 11: Start round 2 (promotes next→role)
    # =========================================================================
    debug "Step 11: Starting round 2..."

    # Bob (index 1, master) starts round 2 — Alice queued watcher so she can't
    ROUND2_RESPONSE=$(api_call 1 POST "/api/v1/rooms/$ROOM_ID/round")
    debug "Round 2 response: $ROUND2_RESPONSE"
    info "Round 2 started"

    # =========================================================================
    # STEP 12: Verify round 2 state
    # =========================================================================
    debug "Step 12: Verifying round 2 state..."

    ADMIN_STATE=$(curl -s "$ADMIN_URL/admin/api/rooms" | jq "{\"$ROOM_ID\": .[\"$ROOM_ID\"]}")
    ROOM_STATE=$(curl -s -L "$BASE_URL/api/v1/rooms/$ROOM_ID")

    # Expected roles after promotion:
    #   Alice:   watcher (was master, next=watcher)
    #   Bob:     master  (unchanged)
    #   Charlie: master  (was player, next=master)
    #   Diana:   player  (unchanged)
    #   Eve:     player  (unchanged)
    #   Frank:   player  (unchanged)
    #   Grace:   player  (unchanged)
    #   Henry:   player  (was watcher, next=player)
    #   Iris:    watcher (unchanged)
    #   Jack:    watcher (unchanged)
    #   Kate:    watcher (unchanged)
    #   Leo:     watcher (unchanged)
    declare -a R2_EXPECTED=(watcher master master player player player player player watcher watcher watcher watcher)

    R2_CORRECT=0
    for i in $(seq 0 $((TOTAL_USERS - 1))); do
        ACTUAL=$(echo "$ADMIN_STATE" | jq -r ".[\"$ROOM_ID\"].users.\"${USER_IDS[$i]}\".relation.role" 2>/dev/null)
        if [[ "$ACTUAL" == "${R2_EXPECTED[$i]}" ]]; then
            R2_CORRECT=$((R2_CORRECT + 1))
            debug "${NAMES[$i]}: role=$ACTUAL (ok)"
        else
            error "${NAMES[$i]}: expected ${R2_EXPECTED[$i]}, got $ACTUAL"
        fi
    done
    assert "Round 2 roles promoted ($R2_CORRECT/$TOTAL_USERS)" "$([[ "$R2_CORRECT" == "$TOTAL_USERS" ]] && echo true || echo false)"

    # Round 2 cards: 6 players now (Diana, Eve, Frank, Grace, Henry + who else?)
    # Players: Diana(3), Eve(4), Frank(5), Grace(6), Henry(7) = 5... wait
    # Actually: Bob=master, Charlie=master, Alice=watcher, Iris/Jack/Kate/Leo=watcher
    # Players: Diana, Eve, Frank, Grace, Henry = 5 players
    # But Henry was watcher→player, so now 5 players (same count, different person)
    R2_CARDS=$(echo "$ROOM_STATE" | jq ".[\"$ROOM_ID\"].cards | length" 2>/dev/null || echo "0")
    R2_PLAYERS=5
    assert "Round 2 cards ($R2_CARDS/$R2_PLAYERS)" "$([[ "$R2_CARDS" == "$R2_PLAYERS" ]] && echo true || echo false)"

    # =========================================================================
    # STEP 13: Test permissions after role swap
    # =========================================================================
    debug "Step 13: Testing permissions after role swap..."

    # 13a: Alice (now watcher) cannot send messages
    ALICE_MSG=$(api_call 0 POST "/api/v1/rooms/$ROOM_ID/message" \
        -H "Content-Type: application/json" -d '{"content": "Alice should be denied"}')
    assert "Alice (new watcher) denied messaging" "$([[ "$ALICE_MSG" == *"watchers cannot send messages"* ]] && echo true || echo false)"

    sleep 0.1

    # 13b: Henry (now player) can send a message
    HENRY_MSG=$(api_call 7 POST "/api/v1/rooms/$ROOM_ID/message" \
        -H "Content-Type: application/json" -d '{"content": "Henry is now a player!"}')
    assert "Henry (new player) can message" "$([[ ! "$HENRY_MSG" == *"error"* ]] && echo true || echo false)"

    sleep 0.1

    # 13c: Charlie (now master) can score a card
    R2_FIRST_CARD=$(echo "$ROOM_STATE" | jq -r ".[\"$ROOM_ID\"].cards | keys[0]" 2>/dev/null)
    CHARLIE_SCORE=$(api_call 2 PATCH "/api/v1/rooms/$ROOM_ID/cards/$R2_FIRST_CARD/score" \
        -H "Content-Type: application/json" -d '{"scored": 9}')
    assert "Charlie (new master) can score" "$([[ "$CHARLIE_SCORE" == *"success"* ]] && echo true || echo false)"

    sleep 0.1

    # 13d: Alice (now watcher) cannot start a round
    ALICE_ROUND=$(api_call 0 POST "/api/v1/rooms/$ROOM_ID/round")
    assert "Alice (new watcher) denied starting round" "$([[ "$ALICE_ROUND" == *"watchers cannot start"* ]] && echo true || echo false)"

    # =========================================================================
    # RESULTS
    # =========================================================================

    if [[ "$ASSERTIONS_PASSED" == "$TOTAL_ASSERTIONS" ]]; then
        success "Integration test PASSED ($ASSERTIONS_PASSED/$TOTAL_ASSERTIONS assertions)"

        info "Test room ready for manual testing!"
        for i in $(seq 0 $((TOTAL_USERS - 1))); do
            info "${NAMES[$i]} (${R2_EXPECTED[$i]}): $BASE_URL/r/$ROOM_ID?code_id=${CODE_IDS[$i]}"
        done
        info "Use 'box test delete' to clean Redis when done"
        exit 0
    else
        error "Integration test FAILED ($ASSERTIONS_PASSED/$TOTAL_ASSERTIONS assertions passed)"
        debug "Admin state: $(echo "$ADMIN_STATE" | jq . 2>/dev/null)"
        info "Test room preserved for debugging"
        info "Use 'box test delete' to clean Redis when done"
        exit 1
    fi
}

# Function to wipe Redis database
test_delete() {
    notice "Starting Redis Database Wipe..."
    warning "This will delete ALL data in Redis!"

    check_services

    FLUSH_RESPONSE=$(curl -s -X POST "$ADMIN_URL/admin/api/flush" 2>/dev/null)
    FLUSH_STATUS=$(echo "$FLUSH_RESPONSE" | jq -r '.status' 2>/dev/null)
    KEYS_DELETED=$(echo "$FLUSH_RESPONSE" | jq -r '.keys_deleted' 2>/dev/null || echo "0")

    if [[ "$FLUSH_STATUS" == "ok" ]]; then
        success "Redis database flushed ($KEYS_DELETED keys deleted)"
        exit 0
    else
        error "Failed to flush Redis database"
        exit 1
    fi
}

# Set up infrastructure
trap cleanup_tunnel EXIT
setup_tunnel
sleep 2

# Execute command
case "$COMMAND" in
    "init")
        test_init
        ;;
    "delete")
        test_delete
        ;;
    *)
        error "Unknown command: $COMMAND"
        usage
        exit 1
        ;;
esac
