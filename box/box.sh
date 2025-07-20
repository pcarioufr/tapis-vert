#!/bin/sh

usage() {
    echo "----------------- box -----------------" 
    echo "A wrapper on docker for The Box" 
    echo "box [-h] [-b] [-d] [-p port] command (opt)"
    echo ""
    echo "Options:"
    echo "    -h (opt)      : this helper"
    echo "    -b (opt)      : (re)build The Box docker image"
    echo "    -d (opt)      : enable debug mode"
    echo "    -p port (opt) : expose port from container to host (like docker -p)"
    echo "                    this option is required for some commands (e.g. admin tunnel)"
    echo ""
    echo "Available commands:"
    echo "    hello           : hello world"
    echo "    ssh ...         : ssh wrapper"
    echo "    deploy ...      : deploy tools"
    echo "    terraform ...   : terraform wrappers"
    echo "    dns ...         : DNS zone management"
    echo "    admin ...       : admin access tools"
    echo "    (no command)    : opens a bash shell"
    echo ""
    echo "Examples:"
    echo "    box -d deploy -p webapp     # Debug mode for partial deployment"
    echo "    box -p 8000 admin tunnel    # Expose port 8000 for admin tunnel"
    echo "    box -p 8001 admin tunnel    # Use different port to avoid conflicts"
}

# Port mappings and environment variables for docker compose run
# NOTE: docker compose run ignores port mappings from compose.yml 
# (only docker compose up uses them), so we need explicit -p flags
PORT_MAPPINGS=""
ENV_VARS=""

while getopts "hbdp:" option; do
case ${option} in
    h) usage && exit 0 ;;
    b) _b=1 ;;
    d) 
        ENV_VARS="${ENV_VARS} -e DEBUG=1"
        echo "debug mode enabled"
        ;;
    p) 
        PORT_MAPPINGS="-p ${OPTARG}:${OPTARG}"
        ENV_VARS="${ENV_VARS} -e EXPOSED_PORT=${OPTARG}"
        [[ "${ENV_VARS}" == *"DEBUG=1"* ]] && echo "EXPOSED_PORT=${OPTARG}"
        ;;
    *) usage && exit 1 ;;
    esac
done
shift $(($OPTIND-1))

if [ -n "${_b}" ] # -b option
then # build command
    docker compose build ubuntu
    exit 0
fi

if [ -z "${*}" ] # empty command line

then # opens terminal
    # NOTE: Using explicit ${PORT_MAPPINGS} and ${ENV_VARS} because docker compose run 
    # doesn't use port mappings from compose.yml file and needs explicit env vars
    docker compose \
        run -it --rm \
        ${PORT_MAPPINGS} \
        ${ENV_VARS} \
        ubuntu /bin/bash

else # runs a script
    # NOTE: Using explicit ${PORT_MAPPINGS} and ${ENV_VARS} because docker compose run 
    # doesn't use port mappings from compose.yml file and needs explicit env vars
    docker compose \
        run -it --rm \
        ${PORT_MAPPINGS} \
        ${ENV_VARS} \
        ubuntu /opt/box/main ${@}

fi