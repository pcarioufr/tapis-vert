# Tapis Vert - Unified App (Admin + Public routes)
# Includes full feature set: auth, rooms, admin, QR codes, etc.
FROM python:3.13.3-alpine3.20
WORKDIR /flask

RUN apk update
RUN apk add --no-cache jpeg-dev zlib-dev build-base curl

# Copy redis-orm package from libs directory for local installation
COPY libs/redis-orm /tmp/redis-orm

# Install build tools first for modern Python packages
RUN pip3 install --upgrade pip setuptools>=61.0 wheel

# Install all dependencies including redis-orm via requirements.txt
COPY flask/.build/requirements.txt /flask/build/requirements.txt 
RUN pip3 install -r build/requirements.txt 