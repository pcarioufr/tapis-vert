#!/bin/bash

for f in /opt/box/libs/* ; do source $f; done

debug "terraform $@"

CMD=${1}
TF_OPTS="-chdir=/data/terraform"

if [ "$CMD" == "login" ] ; then
    terraform login
    exit 0 
fi

if [ "$CMD" == "init" ] ; then
    terraform ${TF_OPTS} init ${@:2}
    exit 0 
fi

if [ "$CMD" == "output" ] ; then
    echo $(terraform ${TF_OPTS} output -json ${@:2}) | jq -r 
    exit 0 
fi

terraform ${TF_OPTS} ${@}
