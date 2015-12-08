#!/bin/bash
set -ex

# https://github.com/OpenVPN/easy-rsa/blob/master/doc/EasyRSA-Readme.md

# The CN can be passed in as the first argument, if empty use address@timestamp
cn=${1:-`unit-get public-address`@`date +%s`}

if [ -d easy-rsa ]; then
  echo "The easy-rsa directory already exists."
else
  # Clone the latest easy-rsa scripts, so we can use subject-alt-name.
  git clone https://github.com/OpenVPN/easy-rsa.git
fi
cd easy-rsa/easyrsa3/

# Initalize easy-rsa so a Certificate of Authority can be created.
./easyrsa init-pki 2>&1 

# Create the Certificate Authority, select a name called the Common Name (CN.)
# This name is purely for display purposes and can be set as you like.
./easyrsa --batch "--req-cn=${cn}" build-ca nopass 2>&1 > /dev/null

# Kubernetes keeps the certificates in /srv/kubernetes
mkdir -p /srv/kubernetes
chmod 770 /srv/kubernetes

# Copy the Certificate Authority to the Kubernetes certificate directory.
install -m 660 pki/ca.crt /srv/kubernetes/ca.crt

# Generate the server certifictes and client certificates.
./create-certs.sh
