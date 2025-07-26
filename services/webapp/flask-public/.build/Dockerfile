# Tapis Vert - Public App (User-facing)
# Includes full feature set: auth, rooms, QR codes, etc.
FROM python:3.13.3-alpine3.20
WORKDIR /flask

RUN apk update
RUN apk add --no-cache jpeg-dev zlib-dev build-base curl

# Copy redis-orm package from libs directory for local installation
COPY libs/redis-orm /tmp/redis-orm

# Install all dependencies including redis-orm via requirements.txt
COPY flask-public/.build/requirements.txt /flask/build/requirements.txt 
RUN pip3 install --upgrade pip
RUN pip3 install -r build/requirements.txt
