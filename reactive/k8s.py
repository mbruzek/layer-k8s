import os

from shlex import split
from subprocess import check_call

from charms.reactive import set_state
from charms.reactive import when
from charms.reactive import when_not

from charmhelpers.core.hookenv import status_set
from charmhelpers.core.templating import render

from os import getenv
from contextlib import contextmanager

@when('docker.available')
@when_not('etcd.available')
def relation_message():
    '''Take over messaging to let the user know they are pending a relationship
    to the ETCD cluster before going any further. '''
    status_set('waiting', 'Relate me to ETCD')


@when('etcd.available')
@when_not('kubernetes-master.available')
def master(etcd):
    '''Install and run the hyperkube container that starts kubernetes-master.
    This actually runs the kubelet, which in turn runs a pod that contains the
    other master components.
    '''
    render_manifest(etcd)
    status_set('maintenance', 'Starting the kubernetes master container')
    with chdir('dockerfiles/hyperkube'):
        cmd = "docker-compose up -d"
        check_call(split(cmd))
    set_state('kubernetes-master.available')
    set_state('proxy.available')
    # TODO: verify with juju action-do kubernetes/0 get-credentials
    status_set('active', 'Kubernetes is started. verify with: kubectl get pods')


@when('proxy.available')
@when_not('kubectl.downloaded')
def download_kubectl():
    '''Download the kubectl binary to test and interact with the cluster.'''
    status_set('maintenance', 'Downloading the kubectl binary')
    cmd = 'wget -nv -O /usr/local/bin/kubectl https://storage.googleapis.com/' \
          'kubernetes-release/release/v1.0.1/bin/linux/amd64/kubectl'
    check_call(split(cmd))
    cmd = 'chmod +x /usr/local/bin/kubectl'
    check_call(split(cmd))
    set_state('kubectl.downloaded')
    status_set('maintenance', 'Kubernetes installed')


def render_manifest(reldata):
    data = {'connection_string': reldata.connection_string()}
    render('master.json', 'files/manifests/master.json', data)


@contextmanager
def chdir(path)
    old_dir = os.getcwd()
    os.chdir(path)
    yield
    os.chdir(old_dir)
