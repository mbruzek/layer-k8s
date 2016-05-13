import os

from shlex import split
from subprocess import call
from subprocess import check_call
from subprocess import check_output

from charms.docker.compose import Compose
from charms.reactive import hook
from charms.reactive import remove_state
from charms.reactive import set_state
from charms.reactive import when
from charms.reactive import when_not

from charmhelpers.core import hookenv
from charmhelpers.core.hookenv import is_leader
from charmhelpers.core.hookenv import leader_set
from charmhelpers.core.hookenv import leader_get
from charmhelpers.core.templating import render
from charmhelpers.core import unitdata
from charmhelpers.core.host import chdir

import tlslib


@when('leadership.is_leader')
def i_am_leader():
    '''The leader is the Kubernetes master node.'''
    leader_set({'master-address': hookenv.unit_private_ip()})


@hook('config-changed')
def config_changed():
    '''If the configuration values change, remove the available states.'''
    config = hookenv.config()
    if any(config.changed(key) for key in config.keys()):
        hookenv.log('Configuration options have changed.')
        # Use the Compose class that encapsulates the docker-compose commands.
        compose = Compose('files/kubernetes')
        if is_leader():
            hookenv.log('Removing master container and kubelet.available state.')  # noqa
            # Stop and remove the Kubernetes kubelet container.
            compose.kill('master')
            compose.rm('master')
            # Remove the state so the code can react to restarting kubelet.
            remove_state('kubelet.available')
        else:
            hookenv.log('Removing kubelet container and kubelet.available state.')  # noqa
            # Stop and remove the Kubernetes kubelet container.
            compose.kill('kubelet')
            compose.rm('kubelet')
            # Remove the state so the code can react to restarting kubelet.
            remove_state('kubelet.available')
        hookenv.log('Removing proxy container and proxy.available state.')
        # Stop and remove the Kubernetes proxy container.
        compose.kill('proxy')
        compose.rm('proxy')
        # Remove the state so the code can react to restarting proxy.
        remove_state('proxy.available')

    if config.changed('version'):
        hookenv.log('Removing kubectl.downloaded state so the new version'
                    ' of kubectl will be downloaded.')
        remove_state('kubectl.downloaded')


@when('tls.server.certificate available')
@when_not('k8s.server.certificate available')
def server_cert():
    '''When the server certificate is available, get the server certificate
    from the charm unit data and write it to the kubernetes directory. '''
    destination_directory = '/srv/kubernetes'
    # Save the server certificate from unitdata to the destination directory.
    tlslib.server_cert(destination_directory)
    set_state('k8s.server.certificate available')


@when('tls.client.certificate available')
@when_not('k8s.client.certficate available')
def client_cert():
    '''When the client certificate is available, get the client certificate
    from the charm unitdata and write it to the kubernetes directory. '''
    destination_directory = '/srv/kubernetes'
    # Copy the client certificate and key to the destination directory.
    tlslib.client_cert(destination_directory)
    set_state('k8s.client.certficate available')


@when('tls.certificate.authority available')
@when_not('k8s.certificate.authority available')
def ca():
    '''When the Certificate Authority is available, copy the CA from the
    /usr/local/share/ca-certificates/k8s.crt to the kubernetes directory. '''
    destination_directory = '/srv/kubernetes'
    # Copy the Certificate Authority to the destination directory.
    tlslib.ca(destination_directory)
    set_state('k8s.certificate.authority available')


@when('kubectl.downloaded', 'leadership.is_leader')
@when_not('skydns.available')
def launch_skydns():
    '''Create the "kube-system" namespace, the skydns resource controller, and
    the skydns service. '''
    # Only launch and track this state on the leader.
    # Launching duplicate SkyDNS rc will raise an error
    # Run a command to check if the apiserver is responding.
    return_code = call(split('kubectl cluster-info'))
    if return_code != 0:
        hookenv.log('kubectl command failed, waiting for apiserver to start.')
        remove_state('skydns.available')
        # Return without setting skydns.available so this method will retry.
        return
    # Check for the "kube-system" namespace.
    return_code = call(split('kubectl get namespace kube-system'))
    if return_code != 0:
        # Create the kube-system namespace that is used by the skydns files.
        check_call(split('kubectl create namespace kube-system'))
    # Check for the skydns replication controller.
    return_code = call(split('kubectl get -f files/manifests/skydns-rc.yml'))
    if return_code != 0:
        # Create the skydns replication controller from the rendered file.
        check_call(split('kubectl create -f files/manifests/skydns-rc.yml'))
    # Check for the skydns service.
    return_code = call(split('kubectl get -f files/manifests/skydns-svc.yml'))
    if return_code != 0:
        # Create the skydns service from the rendered file.
        check_call(split('kubectl create -f files/manifests/skydns-svc.yml'))
    set_state('skydns.available')


@when('docker.available')
@when_not('etcd.available')
def relation_message():
    '''Take over messaging to let the user know they are pending a relationship
    to the ETCD cluster before going any further. '''
    status_set('waiting', 'Waiting for relation to ETCD')


@when('etcd.available', 'tls.server.certificate available')
@when_not('kubelet.available', 'proxy.available')
def start_kubelet(etcd):
    '''Run the hyperkube container that starts the kubernetes services.
    When the leader, run the master services (apiserver, controller, scheduler)
    using the master.json from the rendered manifest directory.
    When not the leader start the node services (kubelet, and proxy).'''
    render_files(etcd)
    # Use the Compose class that encapsulates the docker-compose commands.
    compose = Compose('files/kubernetes')
    status_set('maintenance', 'Starting the Kubernetes services.')
    if is_leader():
        compose.up('master')
        set_state('kubelet.available')
        # Open the secure port for api-server.
        hookenv.open_port(6443)
    else:
        # Start the Kubernetes kubelet container using docker-compose.
        compose.up('kubelet')
        set_state('kubelet.available')
        # Start the Kubernetes proxy container using docker-compose.
        compose.up('proxy')
        set_state('proxy.available')
    status_set('active', 'Kubernetes services started')


@when('kubelet.available', 'leadership.is_leader')
@when_not('kubectl.downloaded')
def download_kubectl():
    '''Download the kubectl binary to test and interact with the cluster.'''
    status_set('maintenance', 'Downloading the kubectl binary')
    version = hookenv.config()['version']
    cmd = 'wget -nv -O /usr/local/bin/kubectl https://storage.googleapis.com' \
          '/kubernetes-release/release/{0}/bin/linux/{1}/kubectl'
    cmd = cmd.format(version, arch())
    hookenv.log('Downloading kubelet: {0}'.format(cmd))
    check_call(split(cmd))
    cmd = 'chmod +x /usr/local/bin/kubectl'
    check_call(split(cmd))
    set_state('kubectl.downloaded')


@when('kubectl.downloaded', 'leadership.is_leader')
@when_not('kubectl.package.created')
def package_kubectl():
    '''Package the kubectl binary and configuration to a tar file for users
    to consume and interact directly with Kubernetes.'''
    context = 'default-context'
    cluster_name = 'kubernetes'
    public_address = hookenv.unit_public_ip()
    directory = '/srv/kubernetes'
    key = 'client.key'
    ca = 'ca.crt'
    cert = 'client.crt'
    user = 'ubuntu'
    port = '6443'
    with chdir(directory):
        # Create the config file with the external address for this server.
        cmd = 'kubectl config set-cluster --kubeconfig={0}/config {1} ' \
              '--server=https://{2}:{3} --certificate-authority={4}'
        check_call(split(cmd.format(directory, cluster_name, public_address,
                                    port, ca)))
        # Create the credentials.
        cmd = 'kubectl config set-credentials --kubeconfig={0}/config {1} ' \
              '--client-key={2} --client-certificate={3}'
        check_call(split(cmd.format(directory, user, key, cert)))
        # Create a default context with the cluster.
        cmd = 'kubectl config set-context --kubeconfig={0}/config {1}' \
              ' --cluster={2} --user={3}'
        check_call(split(cmd.format(directory, context, cluster_name, user)))
        # Now make the config use this new context.
        cmd = 'kubectl config use-context --kubeconfig={0}/config {1}'
        check_call(split(cmd.format(directory, context)))
        # Copy the kubectl binary to this directory
        cmd = 'cp -v /usr/local/bin/kubectl {0}'.format(directory)
        check_call(split(cmd))

        # Create an archive with all the necessary files.
        cmd = 'tar -cvzf /home/ubuntu/kubectl_package.tar.gz ca.crt client.crt client.key config kubectl'  # noqa
        check_call(split(cmd))
        set_state('kubectl.package.created')
        status_set('active', 'kubectl package created')


@when('proxy.available')
@when_not('cadvisor.available')
def start_cadvisor():
    '''Start the cAdvisor container that gives metrics about the other
    application containers on this system. '''
    compose = Compose('files/kubernetes')
    compose.up('cadvisor')
    hookenv.open_port(8088)
    status_set('active', 'cadvisor running on port 8088')
    set_state('cadvisor.available')


@when('sdn.available')
def gather_sdn_data():
    '''Get the Software Defined Network (SDN) information and return it as a
    dictionary.'''
    sdn_data = {}
    # The pillar dictionary is a construct of the skydns files.
    pillar = {}
    # SDN Providers pass data via the unitdata.kv module
    db = unitdata.kv()
    # Ideally the DNS address should come from the sdn cidr.
    subnet = db.get('sdn_subnet')
    if subnet:
        # Generate the DNS ip address on the SDN cidr (this is desired).
        pillar['dns_server'] = get_dns_ip(subnet)
    else:
        # There is no SDN cider fall back to the kubernetes config cidr option.
        pillar['dns_server'] = get_dns_ip(hookenv.config().get('cidr'))
    # The pillar['dns_server'] value is used the skydns-svc.yml file.
    pillar['dns_replicas'] = 1
    # The pillar['dns_domain'] value is ued in the skydns-rc.yml
    pillar['dns_domain'] = hookenv.config().get('dns_domain')
    # Use a 'pillar' dictionary so we can reuse the upstream skydns templates.
    sdn_data['pillar'] = pillar
    return sdn_data


def get_dns_ip(cidr):
    '''Get an IP address for the DNS server on the provided cidr.'''
    # Remove the range from the cidr.
    ip = cidr.split('/')[0]
    # Take the last octet off the IP address and replace it with 10.
    return '.'.join(ip.split('.')[0:-1]) + '.10'


def render_files(reldata=None):
    '''Use jinja templating to render the docker-compose.yml and master.json
    file to contain the dynamic data for the configuration files.'''
    context = {}
    # Load the context data with SDN data.
    context.update(gather_sdn_data())
    # Add the charm configuration data to the context.
    context.update(hookenv.config())
    if reldata:
        # Add the etcd relation data to the context.
        context.update({'connection_string': reldata.connection_string()})
    charm_dir = hookenv.charm_dir()
    rendered_kube_dir = os.path.join(charm_dir, 'files/kubernetes')
    if not os.path.exists(rendered_kube_dir):
        os.makedirs(rendered_kube_dir)
    rendered_manifest_dir = os.path.join(charm_dir, 'files/manifests')
    if not os.path.exists(rendered_manifest_dir):
        os.makedirs(rendered_manifest_dir)

    # Update the context with extra values, arch, manifest dir, and private IP.
    context.update({'arch': arch(),
                    'master_address': leader_get('master-address'),
                    'manifest_directory': rendered_manifest_dir,
                    'public_address': hookenv.unit_get('public-address'),
                    'private_address': hookenv.unit_get('private-address')})

    # Adapted from: http://kubernetes.io/docs/getting-started-guides/docker/
    target = os.path.join(rendered_kube_dir, 'docker-compose.yml')
    # Render the files/kubernetes/docker-compose.yml file that contains the
    # definition for kubelet and proxy.
    render('docker-compose.yml', target, context)

    if is_leader():
        # Source: https://github.com/kubernetes/...master/cluster/images/hyperkube  # noqa
        target = os.path.join(rendered_manifest_dir, 'master.json')
        # Render the files/manifests/master.json that contains parameters for
        # the apiserver, controller, and controller-manager
        render('master.json', target, context)
        # Source: ...master/cluster/addons/dns/skydns-svc.yaml.in
        target = os.path.join(rendered_manifest_dir, 'skydns-svc.yml')
        # Render files/kubernetes/skydns-svc.yaml for SkyDNS service.
        render('skydns-svc.yml', target, context)
        # Source: ...master/cluster/addons/dns/skydns-rc.yaml.in
        target = os.path.join(rendered_manifest_dir, 'skydns-rc.yml')
        # Render files/kubernetes/skydns-rc.yaml for SkyDNS pod.
        render('skydns-rc.yml', target, context)


def status_set(level, message):
    '''Output status message with leadership information.'''
    if is_leader():
         message = '(master) {0}'.format(message)
    hookenv.status_set(level, message)


def arch():
    '''Return the package architecture as a string. Raise an exception if the
    architecture is not supported by kubernetes.'''
    # Get the package architecture for this system.
    architecture = check_output(['dpkg', '--print-architecture']).rstrip()
    # Convert the binary result into a string.
    architecture = architecture.decode('utf-8')
    # Validate the architecture is supported by kubernetes.
    if architecture not in ['amd64', 'arm', 'arm64', 'ppc64le']:
        message = 'Unsupported machine architecture: {0}'.format(architecture)
        status_set('blocked', message)
        raise Exception(message)
    return architecture
