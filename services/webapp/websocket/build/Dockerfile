FROM python:3.11.10-alpine3.20

WORKDIR /websocket

RUN apk update
RUN apk add --no-cache g++ libffi-dev

COPY requirements.txt /websocket/build/requirements.txt 
RUN pip3 install --upgrade pip
RUN pip3 install -r build/requirements.txt
