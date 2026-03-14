#!/bin/bash

usage() {
    echo "----------------- box hello -----------------"
    echo "Smoke test to verify The Box is working."
    echo ""
    echo "Usage: box hello [-h]"
}

if [ "${1}" == "-h" ]; then usage && exit 0; fi

debug this is a debug log!
success "hello world"
