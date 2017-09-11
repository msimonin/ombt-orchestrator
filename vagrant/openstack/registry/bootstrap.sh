#!/usr/bin/env bash

set -x

apt-get update
apt-get -y install python-dev libffi-dev libssl-dev python-setuptools
easy_install pip
pip install -U pip

# maybe not necessary
pip install --upgrade cffi

# https://docs.docker.com/engine/installation/linux/docker-ce/debian/#install-docker-ce
apt-get install -y \
	 apt-transport-https \
	 ca-certificates \
	 curl \
	 gnupg2 \
	 software-properties-common

curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add -

add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/debian \
   $(lsb_release -cs) \
   stable"

apt-get update
apt-get install -y docker-ce

cd /vagrant

# installing kolla
pip install -e .

# starting a local registry
docker run -d -p 5000:5000 --name registry registry:2

#
#{
#    "insecure-registries" : ["myregistrydomain.com:5000"]
#  }
