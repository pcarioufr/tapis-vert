#!/bin/bash

for f in /opt/box/libs/* ; do source $f; done

usage() {
    echo "----------------- box ssh -----------------" 
    echo "A wrapper around various ssh functions." 
    echo "box ssh [-h] [-r] [-L tunnel] command"
    echo "    -h (opt)      : this helper"
    echo "    -r (opt)      : reset known hosts"
    echo "    -n (opt)      : recreate ssh key"
    echo "    command (opt) : command to run remotely"
    echo "                    if none provided, opens a bash shell"
}

while getopts "hL:nr" option; do
case ${option} in
    h) usage && exit 0 ;;
    n) _n=1 ;;
    r) _r=1 ;;
    *) usage && exit 1 ;;
    esac
done
shift $(($OPTIND-1))

debug SSH_OPTS=$SSH_OPTS

if [ -n "${_r}" ]
then
    notice reset known hosts
    rm ~/.ssh/known_hosts
    exit 0
fi

if [ -n "${_n}" ]
then
    notice recreate box ssh key
    ssh-keygen -t rsa -b 4096 -f /home/me/.ssh/id_rsa
    exit 0
fi

notice "using SSH_HOST=$SSH_HOST"

COMMAND=${*}

SSH_PORT="-p 22"

info ssh
ssh -t ${SSH_HOST} ${SSH_PORT} -i /home/me/.ssh/id_rsa ${COMMAND}
