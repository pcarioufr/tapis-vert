FROM nginx:1.27.1

# Install Datadog NGINX Module ##### ##### ##### ##### ##### ##### 

# Update packages to download Datadog NGINX Module 
RUN apt-get update 
RUN apt-get install -y wget tar curl jq

# Download Datadog NGINX Module
COPY datadog-module.sh datadog-module.sh 
RUN chmod +x datadog-module.sh
RUN ./datadog-module.sh 1.27.1

# Certificates to use NGINX as a Datadog Proxy
# https://docs.datadoghq.com/agent/configuration/proxy/?tab=linux#nginx
RUN apt-get install ca-certificates

RUN rm datadog-module.sh

# Install Certbot ##### ##### ##### ##### ##### #####

RUN apt-get install -y certbot
RUN apt-get install -y python3-certbot-nginx