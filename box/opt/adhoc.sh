#!/bin/bash

# Ad-hoc testing script for arbitrary experiments
# This script is safe for Cursor/AI to edit for temporary testing needs

set -e

# Source box libraries
for f in /opt/box/libs/* ; do source $f; done

notice "🧪 Ad-hoc Testing Script"
info "This script runs within the box container with full access to:"
info "- All box configuration variables"
info "- SSH access to remote server"
info "- Admin tunnel capabilities"
info "- Box logging functions (notice, info, success, error, warning, debug)"

success "✅ Hello from the box container!"
info "🔧 Edit this script for your testing needs"

# Example of available functionality:
debug "Debug example - only shows with DEBUG=1"
info "Current SSH_HOST: ${SSH_HOST:-'Not set'}"
info "Current SUBDOMAIN: ${SUBDOMAIN:-'Not set'}"
info "Current DOMAIN: ${DOMAIN:-'Not set'}"

# Example of box logging levels:
notice "📢 This is a notice"
info "ℹ️ This is info"  
success "✅ This is success"
warning "⚠️ This is a warning"
error "❌ This is an error (but script continues)"
debug "🐛 This is debug (only with -d flag)"

success "🎉 Ad-hoc script completed successfully!" 