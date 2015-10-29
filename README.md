# k8s

This charm is an encapsulation of the
[Running Kubernetes locally via Docker](https://github.com/kubernetes/kubernetes/blob/master/docs/getting-started-guides/docker.md)
document.  The charm implements the Kubernetes Docker commands using the
reactive pattern and the `layer:docker`.  For more information please read the
[Juju Charms documentation](https://jujucharms.com/docs/devel/authors-charm-composing)


# Deployment

```
juju deploy local:trusty/k8s
```
There are no configuration for the charm at this time.

**Version**: Set the version of hyperkube image to deploy

**cidr**: Set the IP range for the kubernetes cluster. eg: 10.1.0.0/16


## State Events:

 **Kubelet.available** - Cluster apiserver, and scheduler have been started

 **Proxy.available** - Cluster service proxy has been started

 **kubectl.downloaded** - Denotes the availability of the `kubectl` cli 

# Contact

 * Charm Author: Matthew Bruzek &lt;Matthew.Bruzek@canonical.com&gt;
 * Charm Contributor: Charles Butler &lt;Charles.Butler@canonical.com&gt;

