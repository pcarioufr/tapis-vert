#!/bin/bash

for f in /opt/box/libs/* ; do source $f; done

usage() {
    echo "----------------- box tunnel -----------------" 
    echo "SSH tunnel utility for Tapis Vert services."
    echo "box -p port tunnel -r remote_port [-h]"
    echo "    -p port          : local port to expose (required)"
    echo "    -r remote_port   : remote port to tunnel to (required)"
    echo "                       8002 = admin interface"
    echo "                       8003 = redisinsight"
    echo "    -h (opt)         : this helper"
    echo ""
    echo "Examples:"
    echo "    box -p 8000 tunnel -r 8002      # Access admin via localhost:8000"
    echo "    box -p 8000 tunnel -r 8003      # Access RedisInsight via localhost:8000"
    echo "    box -p 9000 tunnel -r 8003      # Access RedisInsight via localhost:9000"
}

create_tunnel() {
    # Check if port was specified with -p flag
    if [ -z "${EXPOSED_PORT}" ]; then
        error "No local port specified"
        error "Usage: box -p <port> tunnel -r <remote_port>"
        error "Example: box -p 8000 tunnel -r 8002"
        exit 1
    fi
    
    # Check if remote port was specified with -r flag
    if [ -z "${REMOTE_PORT}" ]; then
        error "No remote port specified"
        error "Usage: box -p <port> tunnel -r <remote_port>"
        error "Example: box -p 8000 tunnel -r 8002"
        exit 1
    fi
    
    # Validate remote port
    if [[ "${REMOTE_PORT}" != "8002" && "${REMOTE_PORT}" != "8003" ]]; then
        error "Invalid remote port: ${REMOTE_PORT}"
        error "Allowed values: 8002 (admin) or 8003 (redisinsight)"
        exit 1
    fi
    
    # Determine service name for user feedback
    if [ "${REMOTE_PORT}" == "8002" ]; then
        SERVICE_NAME="Admin"
    else
        SERVICE_NAME="RedisInsight"
    fi
    
    info "Creating SSH tunnel for ${SERVICE_NAME} access..."
    info "Local: localhost:${EXPOSED_PORT} → Remote: localhost:${REMOTE_PORT}"
    info "Press Ctrl+C to close tunnel"

    # Create tunnel: container 0.0.0.0:PORT → remote localhost:REMOTE_PORT
    # External port mapping is handled by docker -p flag
    SSH_PORT="-p 22"
    ssh ${SSH_HOST} ${SSH_PORT} -i /home/me/.ssh/id_rsa -L 0.0.0.0:${EXPOSED_PORT}:localhost:${REMOTE_PORT} -N
}


while getopts "hr:" option; do
case ${option} in
    h) usage && exit 0 ;;
    r) REMOTE_PORT="${OPTARG}" ;;
    *) usage && exit 1 ;;
    esac
done
shift $(($OPTIND-1))

# If there are remaining arguments, show error
if [ -n "$1" ]; then
    error "Unknown argument: $1"
    usage
    exit 1
fi

# Execute tunnel creation
create_tunnel

