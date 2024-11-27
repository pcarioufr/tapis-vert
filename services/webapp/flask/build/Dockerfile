FROM python:3.13.0-alpine3.20
WORKDIR /flask

# Installing zlib, dependency for qrcode
RUN apk add --no-cache jpeg-dev zlib-dev


COPY requirements.txt /flask/build/requirements.txt 
RUN pip3 install --upgrade pip
RUN pip3 install -r build/requirements.txt
