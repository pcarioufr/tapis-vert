#!/bin/bash

for f in /opt/box/libs/* ; do source $f; done

usage() {
    echo "----------------- box admin -----------------" 
    echo "Admin access utility for Tapis Vert."
    echo "box admin [-h] [command]"
    echo ""
    echo "Commands:"
    echo "    tunnel        : Create SSH tunnel for admin access"
    echo "                    Maps localhost:8002 → server admin interface"
    echo "    list          : Quick admin interface link after tunnel"
    echo "    api           : Test admin API connectivity"
    echo "    -h            : Show this help"
    echo ""
    echo "Usage examples:"
    echo "    box admin tunnel     # Start tunnel, then visit http://localhost:8002/admin/list"
    echo "    box admin api        # Test admin API via tunnel"
}

admin_tunnel() {
    notice "Creating SSH tunnel for admin access..."
    notice "Local admin interface will be available at:"
    notice "  → http://localhost:8002/admin/list"
    notice "  → http://localhost:8002/admin/redis"
    notice ""
    notice "Press Ctrl+C to close tunnel"
    notice "using SSH_HOST=$SSH_HOST"
    
    # Create tunnel: local 8002 → remote localhost:8002 (admin nginx)
    ssh -f ${SSH_HOST} -p 22 -L 8002:localhost:8002 -N
}

admin_list() {
    notice "Admin interface URLs (after creating tunnel):"
    notice "  → Main Dashboard: http://localhost:8002/admin/list"
    notice "  → Redis Debug:    http://localhost:8002/admin/redis"
    notice ""
    notice "To create tunnel: box admin tunnel"
}

admin_api() {
    notice "Testing admin API connectivity..."
    
    # Check if tunnel is active
    if ! curl -s --connect-timeout 2 http://localhost:8002/admin/api/rooms > /dev/null; then
        error "Admin tunnel not active. Run: box admin tunnel"
        exit 1
    fi
    
    notice "✅ Admin tunnel is active"
    notice "Testing admin API endpoints..."
    
    echo "📊 Rooms:"
    curl -s http://localhost:8001/admin/api/rooms | head -c 200
    echo ""
    
    echo "👥 Users:"
    curl -s http://localhost:8001/admin/api/users | head -c 200
    echo ""
    
    echo "🔑 Codes:"
    curl -s http://localhost:8001/admin/api/codes | head -c 200
    echo ""
}

# Parse arguments
case "${1}" in
    tunnel)
        admin_tunnel
        ;;
    list)
        admin_list
        ;;
    api)
        admin_api
        ;;
    -h|--help|"")
        usage
        ;;
    *)
        error "Unknown command: ${1}"
        usage
        exit 1
        ;;
esac 