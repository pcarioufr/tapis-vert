#!/bin/bash

for f in /opt/box/libs/* ; do source $f; done

usage() {
    echo "----------------- box deploy -----------------" 
    echo "Deploy content to server." 
    echo "box ssh [-h] [-r] [-L tunnel] command"
    echo "    -h (opt)      : this helper"
    echo "    -d (opt)      : directory to deploy within ./service (e.g. webapp)"
    echo "    -p (opt)      : specific file to patch ./service (e.g. .env)"
}

SRC="/data/services/* /data/services/.env"
DST=/home/ubuntu/services

while getopts "hd:p:" option; do
case ${option} in
    h) usage && exit 0 ;;
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


notice "using SSH_HOST=$SSH_HOST"
notice "update box/bin/box to change this variable"

SSH_PORT="-p 22"
SCP_PORT="-P 22"

if [ "$PATCH" != "1" ]; then
    warning "purge ${DST} folder content on ${SSH_HOST} server"
    ssh ${SSH_HOST} ${SSH_PORT} "mkdir ${DST} > /dev/null 2>&1"
    ssh ${SSH_HOST} ${SSH_PORT} "sudo rm -r ${DST}/* > /dev/null 2>&1"
fi

info "upload ${SRC} -> ${SSH_HOST}:${DST}"
cmd=$(scp -pr ${SCP_PORT} ${SRC} ${SSH_HOST}:${DST} 2>&1)

[ $? -eq 0 ] || error "scp failed" && echo $cmd
