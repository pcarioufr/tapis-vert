#!/bin/bash

for f in /opt/box/libs/* ; do source $f; done

usage() {
    echo "----------------- box dns -----------------" 
    echo "Manage DNS zones via Infomaniak API" 
    echo "box dns [-h] [command]"
    echo "    -h              : this helper"
    echo "    get             : get current DNS zone records"
    echo "    update          : update subdomain A/AAAA records with config values"
}

# API Configuration
API_BASE="https://api.infomaniak.com/2"
CONTENT_TYPE="Content-Type: application/json"

# Check required configuration
check_dns_config() {
    if [ -z "$INFOMANIAK_TOKEN" ]; then
        error "INFOMANIAK_TOKEN not set in config"
        exit 1
    fi
    
    if [ -z "$DOMAIN" ]; then
        error "DOMAIN not set in config"
        exit 1
    fi
}

# Get DNS records for zone
get_zone() {
    local zone="$1"
    info "Getting DNS records for zone: ${zone}"
    
    curl -s \
        -H "Authorization: Bearer ${INFOMANIAK_TOKEN}" \
        -H "${CONTENT_TYPE}" \
        "${API_BASE}/zones/${zone}/records" | jq '.'
}

# Update DNS records using config values
update_dns() {
    info "Updating DNS records for ${SUBDOMAIN}.${DOMAIN}"
    
    # Validate required config
    if [ -z "$DOMAIN" ]; then
        error "DOMAIN not configured in config/.env"
        exit 1
    fi
    
    if [ -z "$SUBDOMAIN" ]; then
        error "SUBDOMAIN not configured in config/.env"
        exit 1
    fi
    
    if [ -z "$INFOMANIAK_TOKEN" ]; then
        error "INFOMANIAK_TOKEN not configured in config/.env"
        exit 1
    fi
    
    # Get current records
    local records_data=$(curl -s \
        -H "Authorization: Bearer ${INFOMANIAK_TOKEN}" \
        -H "${CONTENT_TYPE}" \
        "${API_BASE}/zones/${DOMAIN}/records")
    
    if [ $? -ne 0 ]; then
        error "Failed to fetch DNS records"
        exit 1
    fi
    
    # Find and update A record if IPv4 available
    if [ -n "$PUBLIC_IP_V4" ]; then
        local a_record=$(echo "$records_data" | jq -r ".data[] | select(.source == \"${SUBDOMAIN}\" and .type == \"A\")")
        local a_record_id=$(echo "$a_record" | jq -r ".id")
        local current_a_value=$(echo "$a_record" | jq -r ".target")
        
        if [ "$a_record_id" != "null" ] && [ -n "$a_record_id" ]; then
            info "Found A record (ID: ${a_record_id}), updating from ${current_a_value} to ${PUBLIC_IP_V4}"
            update_single_record "$DOMAIN" "$a_record_id" "$SUBDOMAIN" "A" "$PUBLIC_IP_V4"
        else
            warning "No existing A record found for ${SUBDOMAIN}.${DOMAIN}"
            info "Creating new A record for ${SUBDOMAIN}.${DOMAIN}"
            create_single_record "$DOMAIN" "$SUBDOMAIN" "A" "$PUBLIC_IP_V4"
        fi
    else
        warning "PUBLIC_IP_V4 not available in config"
    fi
    
    # Find and update AAAA record if IPv6 available
    if [ -n "$PUBLIC_IP_V6" ]; then
        local aaaa_record=$(echo "$records_data" | jq -r ".data[] | select(.source == \"${SUBDOMAIN}\" and .type == \"AAAA\")")
        local aaaa_record_id=$(echo "$aaaa_record" | jq -r ".id")
        local current_aaaa_value=$(echo "$aaaa_record" | jq -r ".target")
        
        if [ "$aaaa_record_id" != "null" ] && [ -n "$aaaa_record_id" ]; then
            info "Found AAAA record (ID: ${aaaa_record_id}), updating from ${current_aaaa_value} to ${PUBLIC_IP_V6}"
            update_single_record "$DOMAIN" "$aaaa_record_id" "$SUBDOMAIN" "AAAA" "$PUBLIC_IP_V6"
        else
            warning "No existing AAAA record found for ${SUBDOMAIN}.${DOMAIN}"
            info "Creating new AAAA record for ${SUBDOMAIN}.${DOMAIN}"
            create_single_record "$DOMAIN" "$SUBDOMAIN" "AAAA" "$PUBLIC_IP_V6"
        fi
    else
        warning "PUBLIC_IP_V6 not available in config"
    fi
    
    success "DNS update complete for ${SUBDOMAIN}.${DOMAIN}"
}

# Create DNS record payload
create_dns_payload() {
    local source="$1"
    local record_type="$2"
    local target="$3"
    
    jq -n \
        --arg source "$source" \
        --arg type "$record_type" \
        --arg target "$target" \
        --arg ttl "300" \
        '{
            source: $source,
            type: $type,
            target: $target,
            ttl: ($ttl | tonumber)
        }'
}

# Make DNS API request and handle response
dns_api_request() {
    local method="$1"
    local url="$2"
    local payload="$3"
    local action="$4"
    local zone="$5"
    local source="$6"
    local record_type="$7"
    local target="$8"
    
    debug "${action} with payload: ${payload}"
    
    # Make the API request
    local response=$(curl -s \
        -X "${method}" \
        -H "Authorization: Bearer ${INFOMANIAK_TOKEN}" \
        -H "${CONTENT_TYPE}" \
        -d "${payload}" \
        "${url}")
    
    debug "API Response: ${response}"
    
    # Check if successful
    local result=$(echo "$response" | jq -r '.result')
    if [ "$result" = "success" ]; then
        if [ "$method" = "POST" ]; then
            local new_record_id=$(echo "$response" | jq -r '.data.id')
            success "Created ${record_type} record: ${source}.${zone} -> ${target} (ID: ${new_record_id})"
        else
            success "Updated ${record_type} record: ${source}.${zone} -> ${target}"
        fi
    else
        error "Failed to ${action,,} ${record_type} record for ${source}.${zone}"
        echo "$response" | jq '.'
        return 1
    fi
}

# Update a single DNS record by ID
update_single_record() {
    local zone="$1"
    local record_id="$2"
    local source="$3"
    local record_type="$4"
    local target="$5"
    
    local payload=$(create_dns_payload "$source" "$record_type" "$target")
    local url="${API_BASE}/zones/${zone}/records/${record_id}"
    
    dns_api_request "PUT" "$url" "$payload" "Updating record ${record_id}" \
        "$zone" "$source" "$record_type" "$target"
}

# Create a new DNS record
create_single_record() {
    local zone="$1"
    local source="$2"
    local record_type="$3"
    local target="$4"
    
    local payload=$(create_dns_payload "$source" "$record_type" "$target")
    local url="${API_BASE}/zones/${zone}/records"
    
    dns_api_request "POST" "$url" "$payload" "Creating new record" \
        "$zone" "$source" "$record_type" "$target"
}

# Parse command line arguments
while getopts "h" option; do
case ${option} in
    h) usage && exit 0 ;;
    *) usage && exit 1 ;;
    esac
done
shift $(($OPTIND-1))

CMD=${1}
shift

# Check configuration
check_dns_config

# Execute command
case "$CMD" in
    get)
        get_zone "$DOMAIN"
        ;;
    update)
        update_dns
        ;;
    *)
        usage
        exit 1
        ;;
esac 