#!/bin/bash

usage() {
    echo "----------------- box tunnel -----------------"
    echo "Create an SSH tunnel to access remote services locally."
    echo ""
    echo "Usage: box tunnel [-h] <local_port>:<remote_port>"
    echo ""
    echo "Options:"
    echo "    -h              show this help"
    echo ""
    echo "Remote ports:"
    echo "    8002            admin interface"
    echo "    8003            RedisInsight"
    echo ""
    echo "Examples:"
    echo "    box tunnel 8002:8002              # Admin at localhost:8002/admin/list"
    echo "    box tunnel 8003:8003              # RedisInsight at localhost:8003"
    echo "    box tunnel 9000:8002              # Admin on a different local port"
}

if [ "${1}" == "-h" ] || [ "${1}" == "--help" ]; then usage && exit 0; fi

# Parse local:remote argument
TUNNEL_ARG="${1}"

if [ -z "${TUNNEL_ARG}" ]; then
    error "No tunnel mapping specified"
    error "Usage: box tunnel <local_port>:<remote_port>"
    error "Example: box tunnel 8002:8002"
    exit 1
fi

LOCAL_PORT="${TUNNEL_ARG%%:*}"
REMOTE_PORT="${TUNNEL_ARG##*:}"

if [ -z "${LOCAL_PORT}" ] || [ -z "${REMOTE_PORT}" ] || [ "${LOCAL_PORT}" == "${TUNNEL_ARG}" ]; then
    error "Invalid format: ${TUNNEL_ARG}"
    error "Expected: <local_port>:<remote_port>"
    exit 1
fi

# Determine service name for user feedback
case "${REMOTE_PORT}" in
    8002) SERVICE_NAME="Admin" ;;
    8003) SERVICE_NAME="RedisInsight" ;;
    *)    SERVICE_NAME="port ${REMOTE_PORT}" ;;
esac

info "Creating SSH tunnel for ${SERVICE_NAME} access..."
info "localhost:${LOCAL_PORT} → remote:${REMOTE_PORT}"
info "Press Ctrl+C to close tunnel"

ssh ${SSH_HOST} -p 22 -i "${SSH_KEY}" -L localhost:${LOCAL_PORT}:localhost:${REMOTE_PORT} -N
