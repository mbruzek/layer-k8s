#!/bin/bash
set -ex

# https://github.com/OpenVPN/easy-rsa/blob/master/doc/EasyRSA-Readme.md

private_address=`unit-get private-address`
public_address=`unit-get public-address`

# Clone the latest easy-rsa scripts, so we can use subject-alt-name.
git clone https://github.com/OpenVPN/easy-rsa.git
cd easy-rsa/easyrsa3/

# Initalize easy-rsa so a Certificate of Authority can be created.
./easyrsa init-pki 2>&1 > /dev/null

# Create the Certificate Authority with public address and current time stamp.
./easyrsa --batch "--req-cn=${public_address}@`date +%s`" build-ca nopass 2>&1 > /dev/null
# Create a list of alternate server names with the public and private address.
alt_names="IP:${public_address},IP:${private_address},DNS:`hostname`,DNS:`hostname -f`,DNS:kubernetes,DNS:kubernetes.default"
# Create the server certificate and key for the kubernetes-master (api-server).
./easyrsa --subject-alt-name="${alt_names}" build-server-full kubernetes-master nopass 2>&1 > /dev/null
# Create the client certificate and key for external services such as kubectl.
./easyrsa build-client-full kubecfg nopass 2>&1 > /dev/null

# Kubernetes keeps the certificates in /srv/kubernetes
mkdir -p /srv/kubernetes

# Copy all the keys to the /srv/kubernetes directory.
cp -v pki/ca.crt /srv/kubernetes/ca.crt
# These are for the apiserver.
cp -v pki/issued/kubernetes-master.crt /srv/kubernetes/server.crt
cp -v pki/private/kubernetes-master.key /srv/kubernetes/server.key
# These are for external clients.
cp -v pki/issued/kubecfg.crt /srv/kubernetes/kubecfg.crt
cp -v pki/private/kubecfg.key /srv/kubernetes/kubecfg.key

# Change permissions on all the keys and certificates.
chmod 660 /srv/kubernetes/*

