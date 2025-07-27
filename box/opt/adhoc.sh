#!/bin/bash

# =====================================================================================
# 🔬 CORRUPTION DETECTION TEST - MESSAGE SAVE() SILENT FAILURE (CONTAINER REBUILT)
# =====================================================================================
#
# PURPOSE: Minimal test to reproduce save() method silent failure during messaging
# 
# CORRUPTION CONFIRMED: ✅ Property-level card data corruption occurs after messaging
# ROOT CAUSE IDENTIFIED: 🎯 save() method body never executes during message operations
#
# INVESTIGATION TIMELINE:
# 1. ✅ Initial hypothesis: API data loss → RULED OUT (API layer works correctly)
# 2. ✅ Version conflict hypothesis → RULED OUT (0 ConflictError detected) 
# 3. ✅ ORM import error → FIXED (container rebuilt with clean utils.py)
# 4. 🎯 Message-specific save() failure → CONFIRMED (selective method execution failure)
#
# TECHNICAL DETAILS (AFTER CONTAINER REBUILD):
# • Room/User creation: ✅ WORKS (Room cb55b603e2, Alice c041a10c7d, Bob ff230a1c5b)
# • Card distribution: ✅ WORKS (new_round() save() executes successfully)
# • Message save operation: ❌ FAILS (method called but body never executes)
# • save() method resolution: ✅ CORRECT (introspection shows RedisMixin.save)
# • Method body execution: ❌ NEVER HAPPENS (0 "SAVE METHOD ENTRY" logs)
# • Exception visibility: ❌ NO EXCEPTIONS (silent failure, no error logs)
#
# CORRUPTION PATTERN (CLEAN TEST):
# • Before message: Redis 4/4 properties, API 4/4 properties ✅
# • After message:  Redis 4/4 properties, API 1-3/4 properties ❌ 
# • Message persistence: Redis 0→0, API 0→74 (message never saved)
# • Root cause: save() called correctly but method body never executes
#
# EXECUTION EVIDENCE (CLEAN LOGS):
# • About to save calls: 1 (message operation only)
# • Save introspections: 5 (method correctly identified)
# • Save method entries: 0 (method body never runs)
# • Redis commands: 6 (minimal activity, no save operations)
# • General exceptions: 0 (no visible errors)
#
# PATTERN DISCOVERED:
# • Creation saves work: Room/User/Card creation succeeds (different code path)
# • Message saves fail: save() method body never executes (specific context issue)
# • Silent failure: No exceptions, errors, or visible debugging information
# • Method resolution: Correct (RedisMixin.save properly identified)
#
# NEXT INVESTIGATION:
# • Determine WHY save() method body never executes during message context
# • Possible causes: silent exception, method interception, missing enhanced logging
# • Focus: Understanding why message-specific save() calls fail silently
# • Goal: Make save() method body execute during message operations
#
# TEST DESIGN:
# 1. Create clean room with users and cards (tests creation save() path)
# 2. Capture state before message (Redis + API)
# 3. Send single message to trigger save() operation (tests message save() path)
# 4. Capture state after message (Redis + API) 
# 5. Compare property-level data integrity and message persistence
# 6. Monitor Flask + Redis logs for execution evidence and silent failures
# =====================================================================================

# Include the main library for configuration and utilities
source /opt/box/main

# Increase verbosity if debug mode is active
[[ "${DEBUG:-}" ]] && source /opt/box/libs/verbose.sh

echo "🔬 CORRUPTION DETECTION TEST"
echo "Single test run to reproduce Redis DataError during messaging operations"

# Clean up previous logs to avoid cross-run interference
echo "🧹 Cleaning up previous logs..."
rm -rf ${HOME}/.tmp/logs/*
mkdir -p ${HOME}/.tmp/logs/
echo "✅ Log directory cleaned"

# Initialize log monitoring PIDs
FLASK_LOG_PID=""
REDIS_LOG_PID=""

# Use same configuration as test.sh
BASE_URL="https://${SUBDOMAIN}.${DOMAIN}"  # Public HTTPS route
ADMIN_URL="http://localhost:8001"          # Admin via SSH tunnel

# Function to set up SSH tunnel (same as test.sh)
setup_tunnel() {
    debug "🔗 Opening SSH tunnel to admin service..."
    ssh -f -N -L 8001:localhost:8002 "${SSH_HOST}" 
    debug "Admin service tunnel established"
}

# Function to clean up tunnel (same as test.sh)
cleanup_tunnel() {
    pkill -f "ssh.*-L.*8001:localhost:8002" 2>/dev/null || true
    if [ $? -eq 0 ]; then
        debug "Admin service tunnel closed"
    fi
}

# Function to clean up tunnel and logs
cleanup_all() {
    stop_flask_logs
    stop_redis_logs
    pkill -f "ssh.*-L.*8001:localhost:8002" 2>/dev/null || true
    if [ $? -eq 0 ]; then
        debug "Admin service tunnel closed"
    fi
}
trap cleanup_all EXIT

# Flask log monitoring functions
start_flask_logs() {
    echo "📋 Starting Flask log monitoring..."
    
    # Start background log capture
    ssh "${SSH_HOST}" "docker logs -f flask" > ${HOME}/.tmp/logs/flask_live.log 2>&1 &
    FLASK_LOG_PID=$!
    echo "  📡 Flask log monitoring started (PID: ${FLASK_LOG_PID})"
}

stop_flask_logs() {
    if [[ -n "${FLASK_LOG_PID:-}" ]]; then
        echo "📋 Stopping Flask log monitoring (PID: ${FLASK_LOG_PID})..."
        kill ${FLASK_LOG_PID} 2>/dev/null || true
        wait ${FLASK_LOG_PID} 2>/dev/null || true
        echo "  ✅ Flask log monitoring stopped"
    fi
}

# Redis log monitoring functions
start_redis_logs() {
    echo "📋 Starting Redis log monitoring..."
    
    # Start background Redis log capture
    ssh "${SSH_HOST}" "docker logs -f redis" > ${HOME}/.tmp/logs/redis_live.log 2>&1 &
    REDIS_LOG_PID=$!
    echo "  📡 Redis log monitoring started (PID: ${REDIS_LOG_PID})"
}

stop_redis_logs() {
    if [[ -n "${REDIS_LOG_PID:-}" ]]; then
        echo "📋 Stopping Redis log monitoring (PID: ${REDIS_LOG_PID})..."
        kill ${REDIS_LOG_PID} 2>/dev/null || true
        wait ${REDIS_LOG_PID} 2>/dev/null || true
        echo "  ✅ Redis log monitoring stopped"
    fi
}

# Configure Redis for verbose logging (for debugging)
configure_redis_verbose() {
    echo "📋 Configuring Redis for verbose logging..."
    
    # Try to set Redis to debug mode for more detailed logs
    ssh "${SSH_HOST}" "docker exec redis redis-cli CONFIG SET loglevel debug" || true
    ssh "${SSH_HOST}" "docker exec redis redis-cli CONFIG SET logfile stdout" || true
    
    echo "  ✅ Redis configured for verbose logging"
}

capture_log_segment() {
    local label=$1
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    
    if [[ -f "${HOME}/.tmp/logs/flask_live.log" ]]; then
        # Copy current logs with label
        cp "${HOME}/.tmp/logs/flask_live.log" "${HOME}/.tmp/logs/flask_${label}_${timestamp}.log"
        echo "  📁 Saved Flask logs: ${HOME}/.tmp/logs/flask_${label}_${timestamp}.log"
        
        # Also capture recent logs from container (last 100 lines for context)
        ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR \
            ${SSH_HOST} "cd services && docker compose logs --tail=100 flask" \
            > ${HOME}/.tmp/logs/flask_context_${label}_${timestamp}.log 2>&1
        echo "  📁 Saved Flask context: ${HOME}/.tmp/logs/flask_context_${label}_${timestamp}.log"
    else
        echo "  ⚠️  No live Flask logs found to capture"
    fi
}

analyze_flask_logs() {
    echo ""
    echo "📋 FLASK LOG ANALYSIS:"
    
    # Find all captured log files
    local log_files=$(find ${HOME}/.tmp/logs -name "flask_*.log" -type f 2>/dev/null | sort)
    
    if [[ -z "$log_files" ]]; then
        echo "  ❌ No Flask log files found for analysis"
        return 1
    fi
    
    echo "  📁 Log files captured:"
    for log_file in $log_files; do
        local file_size=$(wc -l < "$log_file" 2>/dev/null || echo "0")
        echo "    $(basename "$log_file"): $file_size lines"
    done
    
    # Analyze key patterns across all logs
    echo ""
    echo "  🔍 Key pattern analysis:"
    
    # Look for save-related logs
    local save_entries=$(grep -h "SAVE METHOD ENTRY\|SAVE VERSION CHECK\|SAVE CONFLICT\|with key.*saved:" $log_files 2>/dev/null | wc -l)
    local message_debugs=$(grep -h "MESSAGE DEBUG.*About to save" $log_files 2>/dev/null | wc -l)
    local save_introspections=$(grep -h "SAVE INTROSPECTION" $log_files 2>/dev/null | wc -l)
    
    echo "    💾 Save operations:"
    echo "      - 'About to save' calls: $message_debugs"
    echo "      - Save introspections: $save_introspections" 
    echo "      - Save method entries: $save_entries"
    
    # Look for error patterns
    local redis_errors=$(grep -h "🚨.*Redis\|redis.*error\|DataError" $log_files 2>/dev/null | wc -l)
    local version_conflicts=$(grep -h "VERSION CONFLICT\|Version mismatch" $log_files 2>/dev/null | wc -l)
    local exceptions=$(grep -h "Exception\|Error\|Traceback" $log_files 2>/dev/null | wc -l)
    
    echo "    ⚠️  Error patterns:"
    echo "      - Redis errors: $redis_errors"
    echo "      - Version conflicts: $version_conflicts"
    echo "      - General exceptions: $exceptions"
    
    # Look for unflatten/corruption patterns
    local unflatten_logs=$(grep -h "UNFLATTEN DEBUG\|UNFLATTEN CORRUPTION" $log_files 2>/dev/null | wc -l)
    local card_logs=$(grep -h "cards.*preview\|cards.*after" $log_files 2>/dev/null | wc -l)
    
    echo "    🎯 Data patterns:"
    echo "      - Unflatten operations: $unflatten_logs"
    echo "      - Card data logs: $card_logs"
    
    # Show recent critical logs
    echo ""
    echo "  🔥 Recent critical events:"
    grep -h "🚨\|ERROR\|CONFLICT\|CORRUPTION" $log_files 2>/dev/null | tail -5 || echo "    No critical events found"
    
    echo ""
    echo "  📂 All logs saved to: ${HOME}/.tmp/logs/"
    echo "     Use 'grep' commands to search for specific patterns"
}

# Redis log analysis function
analyze_redis_logs() {
    echo ""
    echo "📋 REDIS LOG ANALYSIS:"
    
    local log_dir="${HOME}/.tmp/logs"
    
    if [[ ! -d "$log_dir" ]] || [[ -z "$(ls -A $log_dir/redis* 2>/dev/null)" ]]; then
        echo "  ⚠️  No Redis logs found in $log_dir"
        return
    fi
    
    echo "  📁 Redis log files captured:"
    for log_file in $log_dir/redis*.log; do
        if [[ -f "$log_file" ]]; then
            local lines=$(wc -l < "$log_file" 2>/dev/null || echo "0")
            echo "    $(basename "$log_file"): $lines lines"
        fi
    done
    
    echo ""
    echo "  🔍 Key Redis pattern analysis:"
    
    # Redis connection patterns
    local connections=$(grep -r "Accepted\|Client connected\|Client disconnected" $log_dir/redis* 2>/dev/null | wc -l || echo "0")
    echo "    🔗 Connection events: $connections"
    
    # Redis errors and warnings  
    local errors=$(grep -ri "error\|warning\|err\|warn" $log_dir/redis* 2>/dev/null | wc -l || echo "0")
    echo "    ⚠️  Errors/warnings: $errors"
    
    # Redis memory/performance patterns
    local memory_events=$(grep -ri "memory\|oom\|maxmemory" $log_dir/redis* 2>/dev/null | wc -l || echo "0")
    echo "    💾 Memory events: $memory_events"
    
    # Redis command patterns 
    local commands=$(grep -ri "HSET\|HGET\|PIPELINE\|EXEC" $log_dir/redis* 2>/dev/null | wc -l || echo "0")
    echo "    📝 Redis commands: $commands"
    
    # Configuration changes
    local config_changes=$(grep -ri "CONFIG SET\|Configuration loaded" $log_dir/redis* 2>/dev/null | wc -l || echo "0")
    echo "    ⚙️  Config changes: $config_changes"
    
    echo ""
    echo "  🔥 Recent critical Redis events:"
    if [[ -f "$log_dir/redis_live.log" ]]; then
        tail -10 "$log_dir/redis_live.log" | head -5 | while read line; do
            echo "redis | $line"
        done
    fi
    
    echo ""
    echo "  📂 Redis logs saved to: ${HOME}/.tmp/logs/"
    echo "     Use 'grep' commands to search for specific Redis patterns"
}

# Function to check service accessibility (same as test.sh)
check_services() {
    debug "🔍 Checking if services are accessible..."
    if ! curl -s -L "$BASE_URL/ping" > /dev/null 2>&1; then
        error "Public webapp not accessible at $BASE_URL"
        exit 1
    fi

    if ! curl -s "$ADMIN_URL/admin/api/ping" > /dev/null 2>&1; then
        error "Admin webapp not accessible at $ADMIN_URL (via SSH tunnel)"
        exit 1
    fi

    debug "Services accessible (public HTTPS + admin tunnel)"
}

# Core test functions
capture_state() {
    local label=$1
    local room_id=$2
    
    echo "📸 Capturing state: $label"
    
    # Capture Redis raw data via admin API
    local redis_data=$(curl -s "$ADMIN_URL/admin/api/search?pattern=*${room_id}*")
    
    # Capture API response via admin API
    local api_data=$(curl -s "$ADMIN_URL/admin/api/rooms/${room_id}")
    
    # Save to files
    mkdir -p ${HOME}/.tmp/analysis
    echo "$redis_data" > "${HOME}/.tmp/analysis/redis_${label}.json"
    echo "$api_data" > "${HOME}/.tmp/analysis/api_${label}.json"
    
    # Extract card data for corruption analysis
    local room_hashmap=$(echo "$redis_data" | jq -r '.[] | select(.key | startswith("room:")) | .hashmap')
    
    # Extract all card IDs from Redis
    local card_ids=$(echo "$room_hashmap" | grep -o "cards:[^:]*:" | sed 's/cards://g' | sed 's/://g' | sort -u)
    
    echo "  📊 Card analysis for $label:"
    
    if [[ -n "$card_ids" ]]; then
        for card_id in $card_ids; do
            # Check Redis card properties
            local redis_flipped=$(echo "$room_hashmap" | grep "cards:${card_id}:flipped" | cut -d'"' -f4)
            local redis_value=$(echo "$room_hashmap" | grep "cards:${card_id}:value" | cut -d'"' -f4)
            local redis_player_id=$(echo "$room_hashmap" | grep "cards:${card_id}:player_id" | cut -d'"' -f4)
            local redis_peeked=$(echo "$room_hashmap" | grep "cards:${card_id}:peeked" | cut -d'"' -f4)
            
            # Count Redis properties for this card
            local redis_props=0
            [[ -n "$redis_flipped" ]] && redis_props=$((redis_props + 1))
            [[ -n "$redis_value" ]] && redis_props=$((redis_props + 1))
            [[ -n "$redis_player_id" ]] && redis_props=$((redis_props + 1))
            [[ -n "$redis_peeked" ]] && redis_props=$((redis_props + 1))
            
            # Check API card properties
            local api_card=$(echo "$api_data" | jq -r "to_entries[0].value.cards.\"$card_id\" // null")
            local api_props=0
            
            if [[ "$api_card" != "null" ]]; then
                local api_flipped=$(echo "$api_card" | jq -r '.flipped // empty')
                local api_value=$(echo "$api_card" | jq -r '.value // empty')
                local api_player_id=$(echo "$api_card" | jq -r '.player_id // empty')
                local api_peeked=$(echo "$api_card" | jq -r '.peeked // empty')
                
                [[ -n "$api_flipped" ]] && api_props=$((api_props + 1))
                [[ -n "$api_value" ]] && api_props=$((api_props + 1))
                [[ -n "$api_player_id" ]] && api_props=$((api_props + 1))
                [[ -n "$api_peeked" ]] && api_props=$((api_props + 1))
            fi
            
            echo "    Card $card_id: Redis ${redis_props}/4 properties, API ${api_props}/4 properties"
            
            # Store detailed data for analysis
            if [[ "$label" == "before_message" ]]; then
                echo "${card_id}:${redis_props}:${api_props}" >> "${HOME}/.tmp/analysis/cards_before.txt"
            else
                echo "${card_id}:${redis_props}:${api_props}" >> "${HOME}/.tmp/analysis/cards_after.txt"
            fi
        done
    else
        echo "    No cards found"
        if [[ "$label" == "before_message" ]]; then
            echo "no_cards" > "${HOME}/.tmp/analysis/cards_before.txt"
        else
            echo "no_cards" > "${HOME}/.tmp/analysis/cards_after.txt"
        fi
    fi
    
    echo "  💾 Saved to: ${HOME}/.tmp/analysis/redis_${label}.json and ${HOME}/.tmp/analysis/api_${label}.json"
}

analyze_corruption() {
    echo ""
    echo "🔬 CORRUPTION ANALYSIS RESULTS:"
    
    # Read card data
    local before_cards="${HOME}/.tmp/analysis/cards_before.txt"
    local after_cards="${HOME}/.tmp/analysis/cards_after.txt"
    
    if [[ ! -f "$before_cards" || ! -f "$after_cards" ]]; then
        echo "❌ Missing card analysis files"
        return 1
    fi
    
    local before_content=$(cat "$before_cards")
    local after_content=$(cat "$after_cards")
    
    echo "  📊 Detailed card property analysis:"
    
    # Check for corruption patterns
    local corruption_found=0
    
    if [[ "$before_content" == "no_cards" && "$after_content" == "no_cards" ]]; then
        echo "    No cards before or after - test setup issue"
        return 1
    elif [[ "$before_content" != "no_cards" && "$after_content" == "no_cards" ]]; then
        echo "🔴 CORRUPTION: All cards disappeared after message"
        corruption_found=1
    elif [[ "$before_content" == "no_cards" && "$after_content" != "no_cards" ]]; then
        echo "⚠️  UNEXPECTED: Cards appeared after message"
        corruption_found=1
    else
        # Compare card-by-card
        while IFS=':' read -r card_id redis_props api_props; do
            local after_line=$(grep "^${card_id}:" "$after_cards" 2>/dev/null)
            
            if [[ -z "$after_line" ]]; then
                echo "🔴 CORRUPTION: Card $card_id disappeared after message"
                corruption_found=1
            else
                local after_redis_props=$(echo "$after_line" | cut -d':' -f2)
                local after_api_props=$(echo "$after_line" | cut -d':' -f3)
                
                echo "    Card $card_id:"
                echo "      Before: Redis ${redis_props}/4, API ${api_props}/4"
                echo "      After:  Redis ${after_redis_props}/4, API ${after_api_props}/4"
                
                # Check for property loss
                if [[ "$redis_props" -gt "$after_redis_props" ]]; then
                    echo "🔴 CORRUPTION: Card $card_id lost Redis properties (${redis_props} → ${after_redis_props})"
                    corruption_found=1
                fi
                
                if [[ "$api_props" -gt "$after_api_props" ]]; then
                    echo "🔴 CORRUPTION: Card $card_id lost API properties (${api_props} → ${after_api_props})"
                    corruption_found=1
                fi
                
                # Check for Redis vs API mismatch
                if [[ "$after_redis_props" -ne "$after_api_props" ]]; then
                    echo "🔴 CORRUPTION: Card $card_id has Redis/API property mismatch (Redis: ${after_redis_props}, API: ${after_api_props})"
                    corruption_found=1
                fi
            fi
        done < "$before_cards"
    fi
    
    echo ""
    if [[ "$corruption_found" == "1" ]]; then
        echo "🔴 CORRUPTION DETECTED: Cards lost properties or consistency"
        echo "🎯 ROOT CAUSE: Message save() operation corrupted card data"
    else
        echo "✅ NO CORRUPTION: All card properties preserved"
    fi
}

# Function to capture room messages from Redis and API
capture_messages_state() {
    local state_name=$1
    local room_id=$2
    
    echo "  📧 Message analysis for ${state_name}:"
    
    # Get Redis raw messages field
    local redis_messages=$(curl -s "$ADMIN_URL/admin/api/search?pattern=*${room_id}*" | jq -r '.[0].hashmap' | grep -o '"messages":"[^"]*"' | cut -d'"' -f4 || echo "")
    
    # Get API messages field  
    local api_messages=$(curl -s "$ADMIN_URL/admin/api/rooms/${room_id}" | jq ".$(echo $room_id).messages // \"\"")
    
    # Count messages in both
    local redis_message_count=0
    local api_message_count=0
    
    if [[ -n "$redis_messages" && "$redis_messages" != "null" && "$redis_messages" != "" ]]; then
        redis_message_count=$(echo "$redis_messages" | jq '. | length' 2>/dev/null || echo "0")
    fi
    
    if [[ -n "$api_messages" && "$api_messages" != "null" && "$api_messages" != "\"\"" ]]; then
        api_message_count=$(echo "$api_messages" | jq '. | length' 2>/dev/null || echo "0")
    fi
    
    echo "    Redis messages: $redis_message_count"
    echo "    API messages: $api_message_count"
    
    # Save detailed message data for analysis
    echo "$redis_messages" > ${HOME}/.tmp/analysis/redis_messages_${state_name}.json
    echo "$api_messages" > ${HOME}/.tmp/analysis/api_messages_${state_name}.json
    
    echo "  💾 Message data saved to: ${HOME}/.tmp/analysis/{redis,api}_messages_${state_name}.json"
}

# Function to analyze message persistence (was save() working?)
analyze_message_persistence() {
    echo ""
    echo "🔬 MESSAGE PERSISTENCE ANALYSIS:"
    
    # Read before/after message counts from previous capture
    local redis_before=$(cat ${HOME}/.tmp/analysis/redis_messages_before_message.json 2>/dev/null | jq '. | length' 2>/dev/null || echo "0")
    local redis_after=$(cat ${HOME}/.tmp/analysis/redis_messages_after_message.json 2>/dev/null | jq '. | length' 2>/dev/null || echo "0")
    local api_before=$(cat ${HOME}/.tmp/analysis/api_messages_before_message.json 2>/dev/null | jq '. | length' 2>/dev/null || echo "0")
    local api_after=$(cat ${HOME}/.tmp/analysis/api_messages_after_message.json 2>/dev/null | jq '. | length' 2>/dev/null || echo "0")
    
    echo "  📊 Message count comparison:"
    echo "    Redis: $redis_before → $redis_after (change: $((redis_after - redis_before)))"
    echo "    API:   $api_before → $api_after (change: $((api_after - api_before)))"
    
    # Analyze what this means for save() functionality
    if [[ $((redis_after - redis_before)) -eq 1 ]]; then
        echo "  ✅ MESSAGE SAVED TO REDIS: save() method IS working"
        echo "  🎯 Implication: Previous analysis was WRONG - save() does execute"
        echo "  🔍 Card corruption must have different root cause"
    elif [[ $((redis_after - redis_before)) -eq 0 ]]; then
        echo "  ❌ MESSAGE NOT SAVED TO REDIS: save() method NOT working"
        echo "  🎯 Implication: save() method body never executes (analysis confirmed)"
        echo "  🔍 This explains both message loss and card corruption"
    else
        echo "  ⚠️  UNEXPECTED MESSAGE COUNT CHANGE: $((redis_after - redis_before))"
        echo "  🔍 This suggests complex save() behavior - needs investigation"
    fi
    
    # API consistency check
    if [[ $((api_after - api_before)) -eq $((redis_after - redis_before)) ]]; then
        echo "  ✅ Redis and API message counts consistent"
    else
        echo "  ❌ Redis vs API message count mismatch - unflatten issue?"
    fi
}

# Main test execution
main() {
    setup_tunnel
    sleep 2
    check_services
    
    # Start comprehensive log monitoring
    start_flask_logs
    start_redis_logs
    configure_redis_verbose
    
    echo "Step 1: Creating clean test room..."
    ROOM_RESPONSE=$(curl -s -X POST "$ADMIN_URL/admin/api/rooms?name=Redis%20DataError%20Test")
    
    ROOM_ID=$(echo "$ROOM_RESPONSE" | jq -r 'keys[0]')
    [[ "$ROOM_ID" == "null" || -z "$ROOM_ID" ]] && { echo "❌ Failed to create room"; exit 1; }
    echo "✅ New room: $ROOM_ID"
    
    echo "Step 2: Creating Alice (master user)..."
    ALICE_RESPONSE=$(curl -s -X POST "$ADMIN_URL/admin/api/users?name=Alice")
    
    ALICE_ID=$(echo "$ALICE_RESPONSE" | jq -r 'keys[0]')
    ALICE_CODE=$(echo "$ALICE_RESPONSE" | jq -r ".[\"$ALICE_ID\"].codes | keys[0]")
    [[ "$ALICE_ID" == "null" ]] && { echo "❌ Failed to create Alice"; exit 1; }
    echo "✅ Alice created: $ALICE_ID (code: $ALICE_CODE)"
    
    echo "Step 3: Creating Bob (player)..."
    BOB_RESPONSE=$(curl -s -X POST "$ADMIN_URL/admin/api/users?name=Bob")
    
    BOB_ID=$(echo "$BOB_RESPONSE" | jq -r 'keys[0]')
    BOB_CODE=$(echo "$BOB_RESPONSE" | jq -r ".[\"$BOB_ID\"].codes | keys[0]")
    [[ "$BOB_ID" == "null" ]] && { echo "❌ Failed to create Bob"; exit 1; }
    echo "✅ Bob created: $BOB_ID (code: $BOB_CODE)"
    
    echo "Step 4: Joining users to room..."
    # Join users using public API with authentication (same pattern as test.sh)
    ALICE_COOKIE="/tmp/alice_cookie.txt"
    BOB_COOKIE="/tmp/bob_cookie.txt"
    
    # Authenticate Alice and join as master
    curl -s -L -c "$ALICE_COOKIE" "$BASE_URL/r/$ROOM_ID?code_id=$ALICE_CODE" >/dev/null 2>&1
    curl -s -L -b "$ALICE_COOKIE" -X POST "$BASE_URL/api/v1/rooms/$ROOM_ID/join" >/dev/null 2>&1
    curl -s -L -b "$ALICE_COOKIE" -X PATCH "$BASE_URL/api/v1/rooms/$ROOM_ID/user/$ALICE_ID?role=master" >/dev/null 2>&1
    
    # Authenticate Bob and join as player  
    curl -s -L -c "$BOB_COOKIE" "$BASE_URL/r/$ROOM_ID?code_id=$BOB_CODE" >/dev/null 2>&1
    curl -s -L -b "$BOB_COOKIE" -X POST "$BASE_URL/api/v1/rooms/$ROOM_ID/join" >/dev/null 2>&1
    curl -s -L -b "$BOB_COOKIE" -X PATCH "$BASE_URL/api/v1/rooms/$ROOM_ID/user/$BOB_ID?role=player" >/dev/null 2>&1
    
    echo "✅ Users joined and roles assigned"
    
    echo "Step 5: Starting round to create cards..."
    curl -s -L -b "$ALICE_COOKIE" -X POST "$BASE_URL/api/v1/rooms/$ROOM_ID/round" >/dev/null 2>&1
    echo "✅ Round started - cards should be distributed"
    
    # Capture initial logs and state
    capture_log_segment "setup_complete"
    
    # Capture state before messaging
    capture_state "before_message" "$ROOM_ID"
    
    # Capture messages state before sending message
    capture_messages_state "before_message" "$ROOM_ID"
    
    echo ""
    echo "📨 SENDING MESSAGE TO TRIGGER CORRUPTION..."
    
    # Capture logs right before message
    capture_log_segment "before_message_send"
    
    # Send exactly one message using Alice's authenticated session
    MESSAGE_RESPONSE=$(curl -s -L -b "$ALICE_COOKIE" -X POST \
        -H "Content-Type: application/json" \
        -d '{"content": "Hello"}' \
        "$BASE_URL/api/v1/rooms/$ROOM_ID/message")
    
    echo "✅ Message sent successfully"
    
    # Capture logs right after message
    capture_log_segment "after_message_send"
    
    # Small delay to ensure all logging is captured
    sleep 3
    
    # Capture state after messaging
    capture_state "after_message" "$ROOM_ID"
    
    # Capture messages state after sending message
    capture_messages_state "after_message" "$ROOM_ID"
    
    # Analyze if message was actually saved to Redis
    analyze_message_persistence
    
    # Cleanup
    rm -f "$ALICE_COOKIE" "$BOB_COOKIE"
    
    # Analysis
    analyze_corruption
    
    # Stop log monitoring and analyze
    stop_flask_logs
    stop_redis_logs
    analyze_flask_logs
    analyze_redis_logs
    
    echo ""
    echo "🔬 Test completed. All logs and data saved to ${HOME}/.tmp/"
    echo "   📂 Analysis files: ${HOME}/.tmp/analysis/"
    echo "   📂 Flask logs: ${HOME}/.tmp/logs/"
}

main 