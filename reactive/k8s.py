import os

from shlex import split
from subprocess import check_call

from charms.reactive import hook
from charms.reactive import remove_state
from charms.reactive import set_state
from charms.reactive import when
from charms.reactive import when_not

from charmhelpers.core import hookenv
from charmhelpers.core.hookenv import status_set
from charmhelpers.core.templating import render

from contextlib import contextmanager


@hook('config-changed')
def config_changed():
    '''If the configuration values change, remove the available state.'''
    config = hookenv.config()
    if any(config.changed(key) for key in config.keys()):
        hookenv.log('Configuration options have changed.')

        hookenv.log('Removing kubelet service and kubelet.available state.')
        docker_compose_kill_remove('kubelet')
        remove_state('kubelet.available')

        hookenv.log('Removing proxy service and proxy.available state.')
        docker_compose_kill_remove('proxy')
        remove_state('proxy.available')


@when('docker.available')
@when_not('etcd.available')
def relation_message():
    '''Take over messaging to let the user know they are pending a relationship
    to the ETCD cluster before going any further. '''
    status_set('waiting', 'Waiting for relation to ETCD')


@when('etcd.available')
@when_not('kubelet.available')
def master(etcd):
    '''Install and run the hyperkube container that starts kubernetes-master.
    This actually runs the kubelet, which in turn runs a pod that contains the
    other master components.
    '''
    render_files(etcd)
    status_set('maintenance', 'Starting the kubernetes master container')
    with chdir('files/kubernetes'):
        # Start the kubelet container that starts the three master services.
        check_call(split('docker-compose up -d kubelet'))
        set_state('kubelet.available')
        # Start the proxy container
        status_set('maintenance', 'Starting the kubernetes proxy container')
        check_call(split('docker-compose up -d proxy'))
        set_state('proxy.available')
    # TODO: verify with juju action-do kubernetes/0 get-credentials
    status_set('active', 'Kubernetes started')


@when('proxy.available')
@when_not('kubectl.downloaded')
def download_kubectl():
    '''Download the kubectl binary to test and interact with the cluster.'''
    status_set('maintenance', 'Downloading the kubectl binary')
    version = hookenv.config()['version']
    cmd = 'wget -nv -O /usr/local/bin/kubectl https://storage.googleapis.com/' \
          'kubernetes-release/release/{0}/bin/linux/amd64/kubectl'
    cmd = cmd.format(version)
    hookenv.log('Downloading kubelet: {0}'.format(cmd))
    check_call(split(cmd))
    cmd = 'chmod +x /usr/local/bin/kubectl'
    check_call(split(cmd))
    set_state('kubectl.downloaded')
    status_set('active', 'Kubernetes installed')


def render_files(reldata):
    '''Use jinja templating to render the docker-compose.yml and master.json
    file to contain the dynamic data for the configuration files.'''
    context = {}
    context.update(hookenv.config())
    if reldata:
        context.update({'connection_string': reldata.connection_string()})
    charm_dir = hookenv.charm_dir()
    rendered_kube_dir = os.path.join(charm_dir, 'files/kubernetes')
    if not os.path.exists(rendered_kube_dir):
        os.makedirs(rendered_kube_dir)
    rendered_manifest_dir = os.path.join(charm_dir, 'files/manifests')
    if not os.path.exists(rendered_manifest_dir):
        os.makedirs(rendered_manifest_dir)
    # Add the manifest directory so the docker-compose file can have.
    context.update({'manifest_directory': rendered_manifest_dir,
                    'private_address': hookenv.unit_get('private-address')})

    # Render the files/kubernetes/docker-compose.yml file that contains the
    # definition for kubelet and proxy.
    target = os.path.join(rendered_kube_dir, 'docker-compose.yml')
    render('docker-compose.yml', target, context)
    # Render the files/manifests/master.json that contains parameters for the
    # apiserver, controller, and controller-manager
    target = os.path.join(rendered_manifest_dir, 'master.json')
    render('master.json', target, context)


@contextmanager
def chdir(path):
    '''Change the current working directory to a different directory to run
    commands and return to the previous directory after the command is done.'''
    old_dir = os.getcwd()
    os.chdir(path)
    yield
    os.chdir(old_dir)


def docker_compose_kill_remove(service):
    '''Use docker-compose commands to kill and remove the service.'''
    # The docker-compose.yml file is required to run docker-compose commands.
    if os.path.isfile('files/kubernetes/docker-compose.yml'):
        with chdir('files/kubernetes'):
            # The docker-compose command to kill a service.
            kill_command = 'docker-compose kill {0}'.format(service)
            check_call(split(kill_command))
            # The docker-compose command to remove a service (forcefully).
            remove_command = 'docker-compose rm -f {0}'.format(service)
            check_call(split(remove_command))
