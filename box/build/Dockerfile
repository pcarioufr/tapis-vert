FROM ubuntu:24.04

ENV TZ=Europe/Paris
ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm-256color

RUN apt update
RUN apt upgrade -y -qq

# Installed packages 
RUN apt install -y -qq \
    sudo \
    curl wget jq bc unzip vim \
    lsb-release gpg gnupg2 software-properties-common \
    openssh-client openssl \
    opendkim


# HASHICORP SUITE
# https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli
RUN wget -O- https://apt.releases.hashicorp.com/gpg | \
        gpg --dearmor | \
        tee /usr/share/keyrings/hashicorp-archive-keyring.gpg

RUN gpg --no-default-keyring \
        --keyring /usr/share/keyrings/hashicorp-archive-keyring.gpg \
        --fingerprint

RUN echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
        https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
        tee /etc/apt/sources.list.d/hashicorp.list

RUN apt update
RUN apt install -y -qq \
    terraform \
    consul \
    vault

# OPENSTACK
RUN apt install -y -qq \
    python3-openstackclient \
    python3-neutronclient


# Create box user
ENV USERNAME=me

RUN useradd -g users -G sudo -m $USERNAME -d /home/$USERNAME
RUN echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME
RUN chmod 0440 /etc/sudoers.d/$USERNAME
RUN usermod --shell /bin/bash $USERNAME


USER $USERNAME
WORKDIR /home/$USERNAME
