#!/bin/bash

usage() {
    echo "----------------- box ssh -----------------"
    echo "SSH wrapper for remote server access and key management."
    echo ""
    echo "Usage: box ssh [-h] [-r] [-n] [command]"
    echo ""
    echo "Options:"
    echo "    -h              show this help"
    echo "    -k              display public key"
    echo "    -r              remove known hosts entries matching ${DOMAIN}"
    echo "    -n              regenerate SSH key (RSA 4096)"
    echo ""
    echo "Arguments:"
    echo "    command         command to run remotely (optional)"
    echo "                    if omitted, opens an interactive bash shell"
    echo ""
    echo "Examples:"
    echo "    box ssh                                 # Open remote shell"
    echo "    box ssh \"cd services && docker compose ps\"  # Run remote command"
    echo "    box ssh \"docker ps\"                     # Run remote command"
    echo "    box ssh -n                              # Generate new SSH key"
    echo "    box ssh -r                              # Clear known_hosts"
}

while getopts "hknr" option; do
case ${option} in
    h) usage && exit 0 ;;
    k) _k=1 ;;
    n) _n=1 ;;
    r) _r=1 ;;
    *) usage && exit 1 ;;
    esac
done
shift $(($OPTIND-1))

debug SSH_OPTS=$SSH_OPTS

if [ -n "${_k}" ]
then
    if [ -f "${SSH_KEY}.pub" ]; then
        cat "${SSH_KEY}.pub"
    else
        error "No public key found at ${SSH_KEY}.pub"
        exit 1
    fi
    exit 0
fi

if [ -n "${_r}" ]
then
    notice "removing known hosts entries matching ${DOMAIN}"
    ssh-keygen -R "${SUBDOMAIN}.${DOMAIN}" -f "$(dirname "${SSH_KEY}")/known_hosts" 2>/dev/null
    success "removed entries for ${SUBDOMAIN}.${DOMAIN}"
    exit 0
fi

if [ -n "${_n}" ]
then
    notice recreate box ssh key
    ssh-keygen -t rsa -b 4096 -f "${SSH_KEY}"
    exit 0
fi

notice "using SSH_HOST=$SSH_HOST"

COMMAND=${*}

SSH_PORT="-p 22"

# Use -t (force TTY) only for interactive sessions
if [ -z "${COMMAND}" ] && [ -z "${NO_TTY}" ]; then
    SSH_TTY_FLAG="-t"
else
    SSH_TTY_FLAG=""
fi

info ssh
ssh ${SSH_TTY_FLAG} ${SSH_HOST} ${SSH_PORT} -i "${SSH_KEY}" ${COMMAND}
