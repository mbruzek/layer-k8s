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

# Contact

 * Charm Author: Matthew Bruzek &lt;Matthew.Bruzek@canonical.com&gt;
