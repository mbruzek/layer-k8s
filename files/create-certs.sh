#!/bin/bash
set -ex

# https://github.com/OpenVPN/easy-rsa/blob/master/doc/EasyRSA-Readme.md

ca=$1

private_address=`unit-get private-address`
public_address=`unit-get public-address`

if [ -d easy-rsa ]; then
  echo "The easy-rsa directory already exists."
else
  # Clone the latest easy-rsa scripts, so we can use subject-alt-name.
  git clone https://github.com/OpenVPN/easy-rsa.git
fi
cd easy-rsa/easyrsa3/

# Initalize easy-rsa so a Certificate of Authority can be created.
./easyrsa init-pki 2>&1 > /dev/null

cp -v ${ca} pki/

# Create a list of alternate server names with the public and private address.
alt_names="IP:${public_address},IP:${private_address},DNS:`hostname`,DNS:`hostname -f`,DNS:kubernetes,DNS:kubernetes.default"
# Create the server certificate and key for the kubernetes-master (api-server).
./easyrsa --subject-alt-name="${alt_names}" build-server-full kubernetes-master nopass 2>&1 > /dev/null

# Create the client certificate and key for external services such as kubectl.
./easyrsa build-client-full kubecfg nopass 2>&1 > /dev/null

# Kubernetes keeps the certificates in /srv/kubernetes
mkdir -p /srv/kubernetes
chmod 770 /srv/kubernetes

# Copy the certificate and key for the apiserver.
install -m 660 pki/issued/kubernetes-master.crt /srv/kubernetes/server.crt
install -m 660 pki/private/kubernetes-master.key /srv/kubernetes/server.key
# Copy the certificate and key for external clients.
install -m 660 pki/issued/kubecfg.crt /srv/kubernetes/kubecfg.crt
install -m 660 pki/private/kubecfg.key /srv/kubernetes/kubecfg.key
