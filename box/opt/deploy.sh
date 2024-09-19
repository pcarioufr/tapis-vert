#!/bin/bash

for f in /opt/box/libs/* ; do source $f; done

notice "using SSH_HOST=$SSH_HOST"
notice "update box/bin/box to change this variable"

SSH_PORT="-p 22"
SCP_PORT="-P 22"

SRC="/data/services/* /data/services/.env"
DST=/home/ubuntu/services

warning "purge ${DST} folder content on ${SSH_HOST} server"
ssh ${SSH_HOST} ${SSH_PORT} "mkdir ${DST} > /dev/null 2>&1"
ssh ${SSH_HOST} ${SSH_PORT} "sudo rm -r ${DST}/* > /dev/null 2>&1"

info "upload ${SRC} -> ${SSH_HOST}:${DST}"
cmd=$(scp -pr ${SCP_PORT} ${SRC} ${SSH_HOST}:${DST} 2>&1)

[ $? -eq 0 ] || error "scp failed" && echo $cmd
