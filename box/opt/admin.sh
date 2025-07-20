#!/bin/bash

for f in /opt/box/libs/* ; do source $f; done

usage() {
    echo "----------------- box admin -----------------" 
    echo "Admin access utility for Tapis Vert."
    echo "box [-p port] admin [-h] command"
    echo "    -h (opt)      : this helper"
    echo ""
    echo "Commands:"
    echo "    tunnel        : Create SSH tunnel for admin access"
    echo "                    Port specified via required -p flag"
    echo "    ping          : Test admin API directly on server via SSH" 
    echo "                    No port flag needed - tests server directly"
    echo ""
    echo "Examples:"
    echo "    box -p 8000 admin tunnel    # Access via localhost:8000"
    echo "    box -p 8001 admin tunnel    # Access via localhost:8001"  
    echo "    box admin ping              # Test admin API on server"
}

admin_tunnel() {
    # Check if port was specified with -p flag
    if [ -z "${EXPOSED_PORT}" ]; then
        error "No port specified for admin tunnel"
        error "Usage: box -p <port> admin tunnel"
        error "Example: box -p 8000 admin tunnel"
        exit 1
    fi
    
    info "Creating SSH tunnel for admin access on port ${EXPOSED_PORT}..."
    info "Press Ctrl+C to close tunnel"

    # Create tunnel: container 0.0.0.0:PORT → remote localhost:8002 (admin nginx)
    # External port mapping is handled by docker -p flag
    SSH_PORT="-p 22"
    ssh ${SSH_HOST} ${SSH_PORT} -i /home/me/.ssh/id_rsa -L 0.0.0.0:${EXPOSED_PORT}:localhost:8002 -N
}

admin_ping() {
    info "Testing admin API directly on server..."
    
    # Test admin API ping directly on server via SSH
    if ssh ${SSH_HOST} -p 22 -i /home/me/.ssh/id_rsa "curl -s --connect-timeout 3 http://localhost:8002/admin/api/ping" > /dev/null 2>&1; then
        RESPONSE=$(ssh ${SSH_HOST} -p 22 -i /home/me/.ssh/id_rsa "curl -s http://localhost:8002/admin/api/ping")
        success "Admin API is working! Response: $RESPONSE"
    else
        error "Admin API not responding on server"
        error "Check if admin service is running: ssh → docker compose logs flask-admin"
        exit 1
    fi
}


while getopts "h" option; do
case ${option} in
    h) usage && exit 0 ;;
    *) usage && exit 1 ;;
    esac
done
shift $(($OPTIND-1))

# Parse commands
COMMAND=${1}

case "${COMMAND}" in
    tunnel)
        admin_tunnel
        ;;
    ping)
        admin_ping
        ;;
    "")
        usage
        exit 1
        ;;
    *)
        error "Unknown command: ${COMMAND}"
        usage
        exit 1
        ;;
esac 