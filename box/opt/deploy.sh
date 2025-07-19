#!/bin/bash

for f in /opt/box/libs/* ; do source $f; done



# Prepare deployment files (copy source + process templates)
prepare_deployment() {
    DEPLOY_TMP=".tmp/deploy"
    
    debug "Preparing deployment files in ${DEPLOY_TMP}..."
    
    # Create/clean temp deployment directory
    rm -rf "${DEPLOY_TMP}"
    mkdir -p "${DEPLOY_TMP}"
    
    if [ -n "${PARTIAL_PATH}" ]; then
        # Partial deployment - copy only specified path
        SOURCE_PATH="/data/services/${PARTIAL_PATH}"
        
        if [ ! -e "${SOURCE_PATH}" ]; then
            error "Path not found: ${PARTIAL_PATH}"
            exit 1
        fi
        
        # Create parent directories in deployment temp
        PARENT_DIR=$(dirname "${PARTIAL_PATH}")
        if [ "${PARENT_DIR}" != "." ]; then
            mkdir -p "${DEPLOY_TMP}/${PARENT_DIR}"
        fi
        
        # Copy the specific file or directory
        if [ -d "${SOURCE_PATH}" ]; then
            cp -r "${SOURCE_PATH}" "${DEPLOY_TMP}/${PARENT_DIR}/"
            debug "Copied directory ${PARTIAL_PATH} to deployment temp directory"
        else
            cp "${SOURCE_PATH}" "${DEPLOY_TMP}/${PARTIAL_PATH}"
            debug "Copied file ${PARTIAL_PATH} to deployment temp directory"
        fi
    else
        # Full deployment - copy all source files
        cp -r /data/services/* "${DEPLOY_TMP}/"
        debug "Copied all source files to deployment temp directory"
    fi
    
    # Process all template variables in all files
    apply_template_replacements
    
    # Generate .env in deployment directory (only for full deployments or if specifically needed)
    if [ -z "${PARTIAL_PATH}" ] || [[ "${PARTIAL_PATH}" == *"webapp"* ]] || [[ "${PARTIAL_PATH}" == *".env"* ]]; then
        debug "Generating .env file"
        cat > "${DEPLOY_TMP}/.env" << EOF
# Generated from config/.env - DO NOT EDIT MANUALLY
# Edit config/.env instead

# Flask Application
HOST=${HOST}
FLASK_SECRET=${FLASK_SECRET}

# Logging
LEVEL=${LEVEL}

# DataDog Configuration
DD_ENV=${DD_ENV}
DD_VERSION=${DD_VERSION}
DD_CLIENT_TOKEN=${DD_CLIENT_TOKEN}
DD_APPLICATION_ID=${DD_APPLICATION_ID}
DD_SITE=${DD_SITE}
DD_API_KEY=${DD_API_KEY}
DD_TAGS=${DD_TAGS}

# Mixpanel
MP_TOKEN=${MP_TOKEN}

# Redis Configuration
REDIS_HOST=${REDIS_HOST}
REDIS_DATA_DB=${REDIS_DATA_DB}
REDIS_ROUNDS_DB=${REDIS_ROUNDS_DB}
REDIS_USERS_DB=${REDIS_USERS_DB}
REDIS_ROOMS_DB=${REDIS_ROOMS_DB}
REDIS_USERS_ONLINE_DB=${REDIS_USERS_ONLINE_DB}
REDIS_PUBSUB_DB=${REDIS_PUBSUB_DB}
EOF
        info "Generated .env in deployment directory"
    else
        debug "Skipping .env generation for partial deployment"
    fi
    
}

# Apply all template replacements to all files
apply_template_replacements() {
    # Define all template variable replacements
    # Format: "{{template_var}}:${actual_value}"
    # Only include variables that are actually used in template files
    local replacements=(
        "{{domain}}:${DOMAIN}"
        "{{host}}:${SUBDOMAIN}.${DOMAIN}"
    )
    
    debug "Applying template replacements to all files..."
    
    # Find all files in deployment directory (excluding .git and binary files)
    find "${DEPLOY_TMP}" -type f \
        ! -path "*/.git/*" \
        ! -name "*.jpg" ! -name "*.png" ! -name "*.gif" ! -name "*.ico" \
        ! -name "*.ttf" ! -name "*.woff" ! -name "*.woff2" \
        ! -name "*.tar" ! -name "*.zip" ! -name "*.gz" \
    | while read -r file; do
        debug "Processing file: ${file}"
        
        # Apply all replacements to this file
        for replacement in "${replacements[@]}"; do
            template_var="${replacement%%:*}"
            actual_value="${replacement##*:}"
            
            # Check if template variable exists in file, then replace and log
            if grep -q "${template_var}" "${file}" 2>/dev/null; then
                # Count occurrences before replacement
                count=$(grep -o "${template_var}" "${file}" 2>/dev/null | wc -l)
                
                # Apply replacement
                sed -i "s|${template_var}|${actual_value}|g" "${file}" 2>/dev/null || true
                
                # Log the replacement
                relative_file="${file#${DEPLOY_TMP}/}"
                info "Replaced ${count}x${template_var} -> ${actual_value} in ${relative_file}"
            fi
        done
    done
    
    debug "Template processing complete"
}

usage() {
    echo "----------------- box deploy -----------------" 
    echo "Deploy application to server with template processing." 
    echo "box deploy [-h] [-n] [-p path]"
    echo "    -h (opt)      : this helper"
    echo "    -n (opt)      : dry run - process templates but don't deploy"
    echo "    -p path (opt) : deploy only specified file or directory (no trailing slash)"
    echo ""
    echo "Examples:"
    echo "    box deploy                           # Deploy everything"
    echo "    box deploy -p nginx/nginx.conf      # Deploy single file"
    echo "    box deploy -p webapp                 # Deploy webapp directory"
    echo "    box deploy -p webapp/libs/utils      # Deploy nested directory"
    echo "    box deploy -n -p nginx               # Dry run for nginx directory"
}

# Deployment paths (always deploy everything)
DST="/home/ubuntu/services"
DEPLOY_TMP="/home/me/.tmp/deploy"

while getopts "hnp:" option; do
case ${option} in
    h) usage && exit 0 ;;
    n) 
        DRY_RUN=1
        warning "Dry run mode - will process templates but not deploy"
    ;;
    p)
        PARTIAL_PATH="${OPTARG}"
        notice "Partial deployment: ${PARTIAL_PATH}"
    ;;
    *) usage && exit 1 ;;
    esac
done
shift $(($OPTIND-1))

# STEP 1: Always process templates (prepare deployment files)
info "Processing templates and preparing deployment files"
prepare_deployment

# STEP 2: If dry run, show what would be deployed and stop
if [ -n "$DRY_RUN" ]; then
    success "Dry run complete. Processed files ready in ${DEPLOY_TMP}"
    info "Files that would be deployed:"
    find "$DEPLOY_TMP" -type f | sed "s|^${DEPLOY_TMP}|  |"
    exit 0
fi

# STEP 3: Deploy the processed content
debug "using SSH_HOST=$SSH_HOST"
SSH_PORT="-p 22"
SCP_PORT="-P 22"

if [ -z "${PARTIAL_PATH}" ]; then
    # Full deployment - purge entire remote folder
    notice "Purging remote ${DST} folder on ${SSH_HOST}"
    ssh ${SSH_HOST} ${SSH_PORT} "mkdir -p ${DST} > /dev/null 2>&1"
    ssh ${SSH_HOST} ${SSH_PORT} "sudo rm -rf ${DST}/* > /dev/null 2>&1"
else
    # Partial deployment - ensure target directory exists, no purging
    REMOTE_TARGET_DIR="${DST}/$(dirname "${PARTIAL_PATH}")"
    if [ "$(dirname "${PARTIAL_PATH}")" != "." ]; then
        debug "Ensuring remote directory exists: ${REMOTE_TARGET_DIR}"
        ssh ${SSH_HOST} ${SSH_PORT} "mkdir -p ${REMOTE_TARGET_DIR} > /dev/null 2>&1"
    else
        debug "Ensuring remote directory exists: ${DST}"
        ssh ${SSH_HOST} ${SSH_PORT} "mkdir -p ${DST} > /dev/null 2>&1"
    fi
    notice "Partial deployment - overwriting only: ${PARTIAL_PATH}"
fi

# Deploy processed files (including hidden files like .env)
info "Uploading ${DEPLOY_TMP}/* (including hidden files) -> ${SSH_HOST}:${DST}"
shopt -s dotglob  # Include hidden files in glob patterns
cmd=$(scp -pr ${SCP_PORT} ${DEPLOY_TMP}/* ${SSH_HOST}:${DST} 2>&1)
shopt -u dotglob  # Reset to default

if [ $? -eq 0 ]; then
    success "Deployment complete"
else
    error "scp failed: $cmd"
    exit 1
fi
