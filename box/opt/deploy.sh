#!/bin/bash

for f in /opt/box/libs/* ; do source $f; done



# Prepare deployment files (copy source + process templates)
prepare_deployment() {
    DEPLOY_TMP=".tmp/deploy"
    
    debug "Preparing deployment files in ${DEPLOY_TMP}..."
    
    # Create/clean temp deployment directory
    rm -rf "${DEPLOY_TMP}"
    mkdir -p "${DEPLOY_TMP}"
    
    # Copy all source files to temp deployment directory
    cp -r /data/services/* "${DEPLOY_TMP}/"
    debug "Copied source files to deployment temp directory"
    
    # Process all template variables in all files
    apply_template_replacements
    
    # Generate .env in deployment directory
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
                info "Replaced ${count} occurrence(s) of ${template_var} -> ${actual_value} in ${relative_file}"
            fi
        done
    done
    
    debug "Template processing complete"
}

usage() {
    echo "----------------- box deploy -----------------" 
    echo "Deploy content to server." 
    echo "box deploy [-h] [-n] [-d directory] [-p file]"
    echo "    -h (opt)      : this helper"
    echo "    -n (opt)      : dry run - prepare files but don't deploy"
    echo "    -d (opt)      : directory to deploy within ./service (e.g. webapp)"
    echo "    -p (opt)      : specific file to patch ./service (e.g. .env)"
}

SRC="/data/services/* /data/services/.env"
DST=/home/ubuntu/services
DEPLOY_TMP="/home/me/.tmp/deploy"

while getopts "hnd:p:" option; do
case ${option} in
    h) usage && exit 0 ;;
    n) 
        DRY_RUN=1
        warning "running deployment in dry run mode"
    ;;
    d) 
        SRC="/data/services/${OPTARG}/*"
        DST="/home/ubuntu/services/${OPTARG}"
    ;;
    p) 
        PATCH=1
        SRC="/data/services/${OPTARG}"
        DST="/home/ubuntu/services/${OPTARG}"
    ;;
    *) usage && exit 1 ;;
    esac
done
shift $(($OPTIND-1))

# Prepare deployment files unless we're doing a specific file patch
if [ "$PATCH" != "1" ]; then
    prepare_deployment
fi

debug "using SSH_HOST=$SSH_HOST"
SSH_PORT="-p 22"
SCP_PORT="-P 22"

# Use prepared deployment files for full deployment, original source for patches
if [ "$PATCH" != "1" ]; then
    ACTUAL_SRC="${DEPLOY_TMP}/*"
else
    ACTUAL_SRC="${SRC}"
fi

# Deploy files unless in dry run mode
if [ -n "$DRY_RUN" ]; then
    success "Dry run complete. Files prepared in ${DEPLOY_TMP}"
    exit 0
fi

# Purge remote folder for full deployments (only when actually deploying)
if [ "$PATCH" != "1" ]; then
    notice "purge ${DST} folder content on ${SSH_HOST} server"
    ssh ${SSH_HOST} ${SSH_PORT} "mkdir ${DST} > /dev/null 2>&1"
    ssh ${SSH_HOST} ${SSH_PORT} "sudo rm -r ${DST}/* > /dev/null 2>&1"
fi

info "upload ${ACTUAL_SRC} -> ${SSH_HOST}:${DST}"
cmd=$(scp -pr ${SCP_PORT} ${ACTUAL_SRC} ${SSH_HOST}:${DST} 2>&1)

[ $? -eq 0 ] || error "scp failed" && echo $cmd
