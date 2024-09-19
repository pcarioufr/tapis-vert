#!/bin/bash

# download latest recommended SSL params
curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "/etc/letsencrypt/options-ssl-nginx.conf"
curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "/etc/letsencrypt/ssl-dhparams.pem"

email=pcoid@pm.me
size=4096
get_certificate () {
    certbot --nginx -n --agree-tos -m $email --rsa-key-size $size --redirect --https-port $2 -d $1
}

get_certificate $host "tapis-vert.pcariou.fr" 443


# reload NGINX configuration
echo "reload NGINX configuration"
nginx -s reload

