# Tapis Vert - Admin App (Localhost only)
# Minimal dependencies for admin functionality only
FROM python:3.13.3-alpine3.20
WORKDIR /flask

RUN apk update
RUN apk add --no-cache build-base curl

COPY requirements.txt /flask/build/requirements.txt 
RUN pip3 install --upgrade pip
RUN pip3 install -r build/requirements.txt
