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

_Autocomplete_

```bash
source <(kubectl completion bash)>
source <(kubectl completion zsh)>
```

## Kubernetes Pods

A pod is the smallest unit in a Kubernetes cluster. It contains one or more
pods.

* All containers in one pod will always end up on the same node.
* Applications in the same Pod share the same IP address, port space and
  hostname.
* Applications running in the same pod can communicate over System V IPC or
  POSIX message queues (IPC namespace).
* Applications in different pods are isolated from each other.

### The Pod Manifest

The Pod manifest is a text-file representation of the Kubernetes API object.
Kubernetes is a proponent of declarative configuration.

This means that you write down the desired state of the world in a
configuration then submit that configuration to a service transforms the
service to the desired state.

_Creating a Pod_

```bash
$ kubectl run kuard --image=gcr.io/kuar-demo/kuard-amd64:blue
```

_Delete a Pod_
```bash
$ kubectl delete pods/kuard
```

_Creating A Pod Manifest_

Creating Pod manifests is just as simple as running docker commands.

Given a docker run of...
```bash
$ docker run -d --name kuard \
             --publish 8080:8080 \
             gcr.io/kuar-demo/kuard-amd64:blue
```

The equivalent in a pod manifest is...
```bash
$ cat > kuard-pod.yml <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: kuard
spec:
  containers:
    - image: gcr.io/kuar-demo/kuard-amd64:blue
      name: kuard
      ports:
        - containerPort: 8080
          name: http
          protocol: TCP
EOF


```

### Accessing a pod

_Port forward_

```bash
$ kubectl port-forward kuard 8080:8080
```

_Logs_


```bash
$ kubectl logs kuard [-f] [--previous]
```

* `-f` flag will follow the log
* `--previous` print the logs from the previous instance of the container.

### Running Commands in Your Container with exec

```bash
$ kubectl exec kuard date
```

```bash
$ kubectl exec -it kuard -- /bin/bash -l
```

### Copying Files to and from Containers

```bash
$ kubectl cp <pod-name>:/captures/capture3.txt ./capture3.txt
```

```bash
$ kubectl cp $HOME/config.txt <pod-name>:/config.txt
```

## Health Checks

Kuberentes provides health checks for applications to restart them if the
process stops working.

The liveness health check runs application specific code (e.g. loading a web
page) to verify that the application is not just still running but is
functioning.

It should be noted that Resources are requested per container, not per pod.

### Liveness Probe

Check if process is health and restart if not
```bash
$ cat > kuard-pod.yml <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: kuard
spec:
  containers:
  - image: gcr.io/kuar-demo/kuard-amd64:blue
    name: kuard
    livenessProbe:
      httpGet:
        path: /healthy
        port: 8080
        initialDelaySeconds: 5
        timeoutSeconds: 1
        periodSeconds: 10
        failureThreshold: 3
    ports:
      - containerPort: 8080
        name: http
        protocol: TCP
EOF
```

### Readiness Probe

Readiness Probes are similar to liveness probes except if a check fails are
removed from the service load balancer.

### Types of Health checks

* tcpSocket - Check if a tcp socket is open.
* exec probes - Executes a script in the container. A non-zero value is a failure. 

## Resource Management

Kubernetes provides radical improvements in resource management due to the
simplified distribution system. This improves resource utilization and
becomes more cost effective due to efficiencies in sharing compute.

Kubernetes allows users to specify two different resource metrics. 

* Resource requests - Specify the minimum amount of a resource required to run
  an application.

* Resource limits - specify the maximum amount of a resource that an
  application can consume.

_Resource Request_

Requests are used when scheduling Pods to nodes. The Kubernetes scheduler
will ensure that the sum of all requests of all Pods on a node does not
exceed the capacity of the node.

Requests are a minium.

```bash
$ cat > kuard-pod.yml <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: kuard
spec:
  containers:
    - image: gcr.io/kuar-demo/kuard-amd64:blue
      name: kuard
      resources:
        requests:
          cpu: "500m"
          memory: "128Mi"
      ports:
        - containerPort: 8080
          name: http
          protocol: TCP
EOF
```

_Resource Limits_

```bash
$ cat > kuard-pod.yml <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: kuard
spec:
  containers:
    - image: gcr.io/kuar-demo/kuard-amd64:blue
      name: kuard
      resources:
        requests:
          cpu: "500m"
          memory: "128Mi"
        limits:
          cpu: "1000m"
          memory: "256Mi"
      ports:
        - containerPort: 8080
          name: http
          protocol: TCP
EOF
```

### Data Persistence

_Volumes_

```bash
$ cat > kuard-pod.yml <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: kuard
spec:
  volumes:
    - name: "kuard-datab"
      hostPath:
        path: "/var/lib/kuard"
  containers:
    - image: gcr.io/kuar-demo/kuard-amd64:blue
      name: kuard
      volumeMounts:
        - mountPath: "/data"
          name: "kuard-data"
      ports:
        - containerPort: 8080
          name: http
          protocol: TCP
EOF
```