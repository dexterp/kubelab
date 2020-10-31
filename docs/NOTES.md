# Kubernetes Lab notes

## Cluster components

Many of the components that make up Kubernetes are deployed using Kubernetes
itself.

### Kubernetes Proxy

The Kubernetes proxy is responsible for routing network traffic to
load-balanced services.

The proxy must be present in every node in the cluster. Kubernetes has an API
object named DaemonSet which is used in many clusters to deploy the
Kubernetes proxy and other clusters.

To view the proxies run...
```bash
$ kubectl get daemonSets --namespace=kube-system kube-proxy
NAME         DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR            AGE
kube-proxy   5         5         5       5            5           kubernetes.io/os=linux   6d7h
```

Kubernetes proxies at the core uses Linux Netfilter (iptables). At some point
Kubernetes will probably switch to NFTables which is the replacement for
Netfilter. In some systems the iptables command redirects to NFTables which
means that your Kubernetes cluster is already using NFTables.

### Kubernetes DNS

Kubernetes uses a DNS server to provide Naming and Discovery for services
that are defined in the cluster. The DNS server runs as a replicated service
on the cluster.

Depending on the size of the cluster there may be one or more DNS servers running.

There are two parts to the coredns service

1. A deployment
2. A service

To view the DNS servers run the following commands...
```bash
$ kubectl get deployments --namespace=kube-system coredns
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
coredns   2/2     2            2           6d7h
```

```bash
$ kubectl get services --namespace=kube-system kube-dns
NAME       TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)                  AGE
kube-dns   ClusterIP   10.96.0.10   <none>        53/UDP,53/TCP,9153/TCP   6d7h
```

### Kubernetes UI

The final piece of the Kubernetes component is a GUI. The UI is run as a single replica, but it is still managed by a Kubernetes deployment and service.

In later versions of Kubernetes the UI is not installed by default.

To view the deployments
```bash
$ kubectl get deployments --namespace=kubernetes-dashboard
NAME                        READY   UP-TO-DATE   AVAILABLE   AGE
dashboard-metrics-scraper   1/1     1            1           4m5s
kubernetes-dashboard        1/1     1            1           4m5s
```

To view the services
```bash
$ kubectl get services --namespace=kubernetes-dashboard
NAME                        TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
dashboard-metrics-scraper   ClusterIP   10.107.124.15   <none>        8000/TCP   7m18s
kubernetes-dashboard        ClusterIP   10.98.206.245   <none>        443/TCP    7m19s
```

_Viewing the UI_

Kubectl can be used to access the UI.

Launch the proxy

```bash
$ kubectl proxy
```

Then navigate to the URL `http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/`

## Common kubectl commands

_Switch namespace context_

```bash
$ kubectl config set-context my-context --namespace=my-namespace
$ kubectl config use-context my-context
```

_Viewing Kubernetes API Objects_

Everything within the Kubernetes Ecosystem is represented by a RESTful
resource. Each Kubernetes object has a unique HTTP path.

```bash
$ kubectl get pods cassandra-0 -o jsonpath --template={.status.phase}
```

_Creating Updating and Destroying Kubernetes Objects_

Create
```bash
$ kubectl apply -f obj.yml
```

Update
```bash
$ kubectl apply -f obj.yml
```

Dry Run
```bash
$ kubectl apply -f obj.yml --dry-run
```

Editor
```bash
$ kubectl edit <resource-name> <object-name>
```

View Differences between last applied
```bash
$ kubectl apply -f myobj.yaml view-last-applied
```

Delete
```bash
$ kubectl delete -f obj.yaml
```

Delete 2
```bash
$ kubectl delete <resource-name> <object-name>
```

_Labeling and Annotating Objects_

Labels and annotates are tags for objects.

Create/Overwrite a label
```bash
$ kubectl label [--overwrite] pods bar <name>=<value>
```

Remove a label
```bash
$ kubectl label pods bar <name>
```

_Debugging Commands_

Logs
```bash
$ kubectl logs <pod-name>
```

Run a command
```bash
$ kubectl exec <pod-name> <command>
```

Get a shell
```bash
$ kubectl exec -it <pod-name> -- /bin/bash -l
```

Attach to a running process
```bash
$ kubectl attach -it <pod-name>
```

Copy files to a container
```bash
$ kubectl cp <pod-name>:<path/to/remote/file> <path/to/local/file>
```

Access a pod through the network
```bash
$ kubectl port-forward <pod-name> <local-port>:<remote-port>
```

Top Nodes
```bash
$ kubectl top nodes
```

Top pods
```bash
$ kubectl top pods
```
