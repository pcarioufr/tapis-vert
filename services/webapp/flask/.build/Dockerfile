FROM python:3.13.3-alpine3.20
WORKDIR /flask

RUN apk update
RUN apk add --no-cache jpeg-dev zlib-dev build-base curl

# Install rustup and set up the Rust toolchain
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y && \
    /root/.cargo/bin/rustup install stable && \
    /root/.cargo/bin/rustup default stable
ENV PATH="/root/.cargo/bin:${PATH}"

COPY requirements.txt /flask/build/requirements.txt 
RUN pip3 install --upgrade pip
RUN pip3 install -r build/requirements.txt
