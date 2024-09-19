FROM python:3.9-alpine3.13

WORKDIR /websocket

RUN apk update
RUN apk add --no-cache g++ libffi-dev

COPY requirements.txt /websocket/build/requirements.txt 
RUN pip3 install --upgrade pip
RUN pip3 install -r build/requirements.txt

ENV PYTHONPATH "${PYTHONPATH}:/lib"