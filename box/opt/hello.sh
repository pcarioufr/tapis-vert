#!/bin/bash

for f in /opt/box/libs/* ; do source $f; done

success "hello world"
