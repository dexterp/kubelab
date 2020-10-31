# TASKS  

A list of tasks' when working with Kubernetes

## Cluster Administration

### Cluster Management

_Get Cluster Information_

```bash
$ kubectl cluster-info
Kubernetes master is running at https://192.168.115.10:6443
KubeDNS is running at https://192.168.115.10:6443/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy
```

### Nodes

_list nodes_

```bash
$ kubectl get nodes
```

_describe node_

```bash
$ kubectl describe nodes kuberun1
```

## Container/Application Management

### Deploying a container application

_Deploying an example container application_

```bash
$ kubectl create deployment kubernetes-bootcamp --image=gcr.io/google-samples/kubernetes-bootcamp:v1
deployment.apps/kubernetes-bootcamp created
```
_List deployments_

```bash
$ kubectl get deployments
NAME                  READY   UP-TO-DATE   AVAILABLE   AGE
kubernetes-bootcamp   1/1     1            1           3m22s
```

### Accessing the application through a proxy

The API server will automatically create an endpoint for each pod, based on
the pod name, that is also accessible through the proxy.

_Start proxy_

```bash
$ kubectl proxy
Starting to serve on 127.0.0.1:8001
```

_Check access_

```bash
$ curl http://localhost:8001/version
```

_Get Pod Name_

```bash
$ kubectl get pods
NAME                                   READY   STATUS    RESTARTS   AGE
kubernetes-bootcamp-57978f5f5d-j4b2f   1/1     Running   0          10m

$ export POD_NAME=$(kubectl get pods -o go-template --template '{{range .items}}{{.metadata.name}}{{"\n"}}{{end}}')
$ echo Name of the Pod: $POD_NAME
Name of the Pod: kubernetes-bootcamp-57978f5f5d-j4b2f
```

_Curl Application_

```bash
$ curl http://localhost:8001/api/v1/namespaces/default/pods/$POD_NAME/proxy
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-57978f5f5d-j4b2 | v=1
```

_Getting a shell on a container_

```bash
$ kubectl exec --stdin --tty $POD_NAME -- /bin/bash
root@kubernetes-bootcamp-57978f5f5d-j4b2f:/# 
```

_Getting a shell when a pod contains more then one container_
```bash
$ kubectl exec -i -t $POD_NAME -pod --container $CONTAINER -- /bin/bash
```

_Describe POD_

To view what containers are inside that Pod and what images are used to build
those containers we run.
```bash
$ kubectl describe pods
```

_View Container Logs_

```bash
$ kubectl logs $POD_NAME
```

_Removing a deployment_

```bash
$ kubectl delete deployment.apps/kubernetes-bootcampdeployment.apps
"kubernetes-bootcamp" deleted
```

### Exposing Services

_List Services_

Only kubernetes is running at the start

```bash
$ kubectl get services
NAME         TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)   AGE
kubernetes   ClusterIP   10.96.0.1    <none>        443/TCP   16h
```

_Expose Service_

```bash
$ kubectl expose deployment/kubernetes-bootcamp --type="NodePort" --port 8080
service/kubernetes-bootcamp exposed
```

_List exposed services_

```bash
$ kubectl get services
NAME                  TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)          AGE
kubernetes            ClusterIP   10.96.0.1      <none>        443/TCP          16h
kubernetes-bootcamp   NodePort    10.98.199.28   <none>        8080:32120/TCP   107s
```

_Setup a node port_

```bash
$ export NODE_PORT=$(kubectl get services/kubernetes-bootcamp -o go-template='{{(index .spec.ports 0).nodePort}}')

$ echo NODE_PORT=$NODE_PORT
NODE_PORT=31753
```

TODO: Make this work in the cluster
```bash
$ curl $(minikube ip):$NODE_PORT
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-765bf4c7b4-k2n8g | v=1
```

### Replica Sets

In this section we will replicate a POD into multiple nodes.


_List available deployments_

List available deployments and choose one that can be replicated

```bash
$ kubectl get deployments
NAME                  READY   UP-TO-DATE   AVAILABLE   AGE
kubernetes-bootcamp   1/1     1            1           8m3s
```
The fields represented in deployments
* NAME - Name of the deployment
* READY - The current/desired replicas
* UP-TO-DATE - The number of replicas that have been updated to achieve the
  desired state.
* AVAILABLE - The number of replicas available to the end user.
* AGE - The amount of time the application has been running.


_List replica sets_

```bash
$ kubectl get rs
NAME                             DESIRED   CURRENT   READY   AGE
kubernetes-bootcamp-57978f5f5d   1         1         1       12m
```

The fields represented in the replica set output
* DESIRED displays the desired number of replicas of the application, which you
  define when you create the Deployment. This is the desired state.
* CURRENT displays how many replicas are currently running.

_Scale out the deployment_

```bash
$ kubectl scale deployments/kubernetes-bootcamp --replicas=4
deployment.apps/kubernetes-bootcamp scaled
```

_Examine the changes_

```bsh
$ kubectl get deployments
NAME                  READY   UP-TO-DATE   AVAILABLE   AGE
kubernetes-bootcamp   4/4     4            4           19m

$ kubectl get rs
NAME                             DESIRED   CURRENT   READY   AGE
kubernetes-bootcamp-765bf4c7b4   4         4         4       17m

$ kubectl get pods -o wide
NAME                                   READY   STATUS    RESTARTS   AGE     IP          NODE       NOMINATED NODE   READINESS GATES
kubernetes-bootcamp-57978f5f5d-2rpzx   1/1     Running   0          107s    10.85.0.2   kuberun3   <none>           <none>
kubernetes-bootcamp-57978f5f5d-5pjhv   1/1     Running   0          2m47s   10.85.0.3   kuberun2   <none>           <none>
kubernetes-bootcamp-57978f5f5d-7j8rx   1/1     Running   0          107s    10.85.0.3   kuberun4   <none>           <none>
kubernetes-bootcamp-57978f5f5d-dcp4j   1/1     Running   0          107s    10.85.0.3   kuberun1   <none>           <none>
```

There are now 4 pods running on 4 different hosts

_Check Load balancing_

Check the the application has been exposed publicly.
```bash
$ kubectl describe services/kubernetes-bootcamp
```

_Create a node port environment variable_

```bash
export NODE_PORT=$(kubectl get services/kubernetes-bootcamp -o go-template='{{(index .spec.ports 0).nodePort}}')
echo NODE_PORT=$NODE_PORT
```

_Curl port_

CURL the port multiple times to check it is being load balanced.

```bash
$ curl $(minikube ip):$NODE_PORT
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-765bf4c7b4-kzr4j | v=1
$ curl $(minikube ip):$NODE_PORT
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-765bf4c7b4-kzr4j | v=1
$ curl $(minikube ip):$NODE_PORT
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-765bf4c7b4-t7x9c | v=1
$ curl $(minikube ip):$NODE_PORT
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-765bf4c7b4-5lp2r | v=1
$ curl $(minikube ip):$NODE_PORT
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-765bf4c7b4-4ddbj | v=1
$ curl $(minikube ip):$NODE_PORT
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-765bf4c7b4-kzr4j | v=1
```

_Scale down the environment_

```bash
$ kubectl scale deployments/kubernetes-bootcamp --replicas=2
deployment.apps/kubernetes-bootcamp scaled
```

_Check the status of the deployments_

```bash
$ kubectl get deployments
NAME                  READY   UP-TO-DATE   AVAILABLE   AGE
kubernetes-bootcamp   2/2     2            2           49m
$ kubectl get pods -o wide
NAME                                   READY   STATUS        RESTARTS   AGE   IP        NODE       NOMINATED NODE   READINESS GATES
kubernetes-bootcamp-765bf4c7b4-4ddbj   1/1     Terminating   0          32m   172.18.0.7   minikube   <none>           <none>
kubernetes-bootcamp-765bf4c7b4-5lp2r   1/1     Running       0          32m   172.18.0.9   minikube   <none>           <none>
kubernetes-bootcamp-765bf4c7b4-kzr4j   1/1     Running       0          49m   172.18.0.4   minikube   <none>           <none>
kubernetes-bootcamp-765bf4c7b4-t7x9c   1/1     Terminating   0          32m   172.18.0.8   minikube   <none>           <none>
$
```