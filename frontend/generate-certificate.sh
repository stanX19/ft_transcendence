#!/usr/bin/env sh
set -eu

certificate_directory="/etc/nginx/certs"
certificate_file="${certificate_directory}/localhost.crt"
key_file="${certificate_directory}/localhost.key"

if [ ! -s "$certificate_file" ] || [ ! -s "$key_file" ]; then
    mkdir -p "$certificate_directory"
    # Development-only self-signed certificate. The SAN covers both URLs used
    # in local evaluation: https://localhost and https://127.0.0.1.
    openssl req -x509 -nodes -newkey rsa:2048 -days 825 \
        -keyout "$key_file" \
        -out "$certificate_file" \
        -subj "/C=XX/ST=Local/L=Local/O=LibraryOS/OU=Development/CN=localhost" \
        -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
    chmod 600 "$key_file"
fi

# To trust the certificate permanently, copy localhost.crt from the running
# web container and import it into the local browser/OS trust store. Otherwise
# open the URL and use the browser's documented local-certificate exception.
