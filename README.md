# k8s

[Kubernetes](https://github.com/kubernetes/kubernetes) is an open
source  system for managing containerized applications across multiple hosts.
Kubernetes uses [Docker](http://www.docker.io/) to package, instantiate and run
containerized applications.

This charm is an encapsulation of the
[Running Kubernetes locally via Docker](https://github.com/kubernetes/kubernetes/blob/master/docs/getting-started-guides/docker.md)
document.  The hyperkube image (`gcr.io/google_containers/hyperkube`) is
currently pulled from a [Google owned container repository
repository](https://cloud.google.com/container-registry/).  For this charm to
work it will need access to the repository to `docker pull` the images.

The charm is implemented in the reactive pattern and uses the
`layer:docker` as a base layer.  For more information please read the
[Juju Charms documentation](https://jujucharms.com/docs/devel/authors-charm-composing)


# Deployment
The k8s charms require a relation to ECTD a distributed key value store
which Kubernetes uses for persistent storage of all of its REST API objects.

```
juju deploy trusty/etcd
juju deploy local:trusty/k8s
juju add-relation k8s etcd
```

# Configuration
For your convenience this charm supports some configuration options to set up
a Kuberentes cluster that works in your environment:  

**version**: Set the version of the Kubernetes containers to deploy.
The default value is "v1.0.6".  Changing the version causes the all the
Kubernetes containers to be restarted.

**cidr**: Set the IP range for the Kubernetes cluster. eg: 10.1.0.0/16


## State Events
This charm makes use of the reactive framework where states are set or removed.
The charm code can respond to these layers appropriately.

 **kubelet.available** - The hyperkube container has been run with the kubelet
 service and configuration that starts the apiserver, controller-manager and
 scheduler containers.

 **proxy.available** - The hyperkube container has been run with the proxy
 service and configuration that handles Kubernetes networking.

 **kubectl.downloaded** - Denotes the availability of the `kubectl` application
 that can be found in `/usr/bin/local/kubectl`

# Kubernetes information

 - [Kubernetes github project](https://github.com/kubernetes/kubernetes)
 - [Kubernetes issue tracker](https://github.com/kubernetes/kubernetes/issues)
 - [Kubernetes Documenation](https://github.com/kubernetes/kubernetes/tree/master/docs)
 - [Kubernetes releases](https://github.com/kubernetes/kubernetes/releases)

# Contact

 * Charm Author: Matthew Bruzek &lt;Matthew.Bruzek@canonical.com&gt;
 * Charm Contributor: Charles Butler &lt;Charles.Butler@canonical.com&gt;
