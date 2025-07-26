FROM python:3.13.3-alpine3.20
WORKDIR /websocket

RUN apk update
RUN apk add --no-cache build-base curl

# Copy redis-orm package from libs directory for local installation
COPY libs/redis-orm /tmp/redis-orm

# Install all dependencies including redis-orm via requirements.txt
COPY websocket/.build/requirements.txt /websocket/build/requirements.txt 
RUN pip3 install --upgrade pip
RUN pip3 install -r build/requirements.txt
