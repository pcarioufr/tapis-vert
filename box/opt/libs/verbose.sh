#!/bin/bash

# https://unix.stackexchange.com/questions/19323/what-is-the-caller-command
# https://askubuntu.com/questions/678915/whats-the-difference-between-and-in-bash
# https://stackoverflow.com/questions/918886/how-do-i-split-a-string-on-a-delimiter-in-bash
stacktrace() {
    local LINE SUB FILE
    
    # Just get the immediate caller (filename:line)
    read LINE SUB FILE < <(caller 1)
    FILEa=(${FILE//// })
    filename="${FILEa[-1]}"
    echo "${filename%.sh}:${LINE} |"
}

NC='\033[0m' # No Color
LRED='\033[0;91m'   ; critical () { echo -e "${LRED}$(stacktrace) $@${NC}"   ; }
RED='\033[0;31m'    ; error ()    { echo -e "${RED}$(stacktrace) $@${NC}"    ; }
ORANGE='\033[0;33m' ; warning ()  { echo -e "${ORANGE}$(stacktrace) $@${NC}" ; }
BLUE='\033[0;34m'   ; notice ()   { echo -e "${BLUE}$(stacktrace) $@${NC}"   ; }
CYAN='\033[0;36m'   ; info ()     { echo -e "${CYAN}$(stacktrace) $@${NC}"   ; }
GREEN='\033[0;32m'  ; success ()  { echo -e "${GREEN}$(stacktrace) $@${NC}"  ; }

GREY='\033[0;90m'   
debug () { if [ -n "${DEBUG}" ] ; then echo -e "${GREY}$(stacktrace) $@${NC}" ; fi ; }

assert () { 
    if [ "$1" -eq "0" ]
    then echo -e "${GREEN}${@:2} ok${NC}" 
    else echo -e "${RED}${@:2} failed${NC}" 
    fi
}