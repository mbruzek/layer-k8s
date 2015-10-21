from shlex import split
from subprocess import check_call

from charms.reactive import set_state
from charms.reactive import when
from charms.reactive import when_not

from charmhelpers.core.hookenv import config
from charmhelpers.core.hookenv import status_set
from charmhelpers.core.templating import render
from os import getcwd


@when('docker.available')
@when_not('etcd.available')
def etcd():
    '''Install and run the etcd container.'''
    status_set('maintenance', 'Starting the etcd container')
    cmd = 'docker run -d --net=host --restart=always ' \
          'gcr.io/google_containers/etcd:2.0.12 ' \
          '/usr/local/bin/etcd --addr=127.0.0.1:4001 ' \
          '--bind-addr=0.0.0.0:4001 --data-dir=/var/etcd/data'
    check_call(split(cmd))
    set_state('etcd.available')
    status_set('maintenance', '')


@when('etcd.available')
@when_not('kubernetes-master.available')
def master():
    '''Install and run the hyperkube container that starts kubernetes-master.
    This actually runs the kubelet, which in turn runs a pod that contains the
    other master components.
    '''
    status_set('maintenance', 'Starting the kubernetes master container')
    cmd = 'docker run -d --net=host --pid=host --privileged=true ' \
          '--restart=always ' \
          '--volume=/:/rootfs:ro ' \
          '--volume=/sys:/sys:ro ' \
          '--volume=/dev:/dev ' \
          '--volume=/var/lib/docker/:/var/lib/docker:rw ' \
          '--volume=/var/lib/kubelet/:/var/lib/kubelet:rw ' \
          '--volume=/var/run:/var/run:rw ' \
          'gcr.io/google_containers/hyperkube:v1.0.6 ' \
          '/hyperkube kubelet --containerized ' \
          '--hostname-override="127.0.0.1" --address="0.0.0.0" ' \
          '--api-servers=http://localhost:8080 ' \
          '--config=/etc/kubernetes/manifests'
    check_call(split(cmd))
    set_state('kubernetes-master.available')
    status_set('maintenance', '')


@when('kubernetes-master.available')
@when_not('proxy.available')
def proxy():
    '''Run the hyperkube container that starts the proxy. Need to have the
    master started for this to work.
    '''
    status_set('maintenance', 'Starting the service proxy container')
    cmd = 'docker run -d --net=host --privileged=true --restart=always ' \
          'gcr.io/google_containers/hyperkube:v1.0.6 ' \
          '/hyperkube proxy --master=http://127.0.0.1:8080 --v=2'
    check_call(split(cmd))
    set_state('proxy.available')
    status_set('maintenance', '')


@when('proxy.available')
@when_not('kubectl.downloaded')
def download_kubectl():
    '''Download the kubectl binary to test and interact with the cluster.'''
    status_set('maintenance', 'Downloading the kubectl binary')
    cmd = 'wget -nv https://storage.googleapis.com/kubernetes-release/' \
          'release/v1.0.1/bin/linux/amd64/kubectl'
    check_call(split(cmd))
    set_state('kubectl.downloaded')
    status_set('maintenance', 'Kubernetes installed')
