#!/bin/sh

usage() {
    echo "----------------- box -----------------" 
    echo "A wrapper on docker for The Box" 
    echo "box [-h] [-b] [-p port] command (opt)"
    echo "    -h (opt)      : this helper"
    echo "    -b (opt)      : (re)build The Box docker image"
    echo "    -p port (opt) : expose port from container to host (like docker -p)"
    echo "                    this option is required for some commands (e.g. admin tunnel)"
    echo "    command (opt) : command to pass to the box entry script"
    echo "                    passing no command opens a bash shell"
    echo ""
    echo "Examples:"
    echo "    box -p 8000 admin tunnel    # Expose port 8000 for admin tunnel"
    echo "    box -p 8001 admin tunnel    # Use different port to avoid conflicts"
}

# Port mappings for docker compose run
# NOTE: docker compose run ignores port mappings from compose.yml 
# (only docker compose up uses them), so we need explicit -p flags
PORT_MAPPINGS=""

while getopts "hbp:" option; do
case ${option} in
    h) usage && exit 0 ;;
    b) _b=1 ;;
    p) 
        PORT_MAPPINGS="-p ${OPTARG}:${OPTARG}"
        export EXPOSED_PORT="${OPTARG}"
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
    # NOTE: Using explicit ${PORT_MAPPINGS} because docker compose run 
    # doesn't use port mappings from compose.yml file
    docker compose \
        run -it --rm \
        ${PORT_MAPPINGS} \
        ubuntu /bin/bash

else # runs a script
    # NOTE: Using explicit ${PORT_MAPPINGS} because docker compose run 
    # doesn't use port mappings from compose.yml file
    docker compose \
        run -it --rm \
        ${PORT_MAPPINGS} \
        ubuntu /opt/box/main ${@}

fi