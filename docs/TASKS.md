# TASKS  

A list of tasks' when working with Kubernetes

## Cluster Administration

### Nodes

_list nodes_

```bash
$ kubectl get nodes
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

The API server will automatically create an endpoint for each pod, based on the pod name, that is also accessible through the proxy.

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

To view what containers are inside that Pod and what images are used to build those containers we run 
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
