# Terms

## POD

A Pod is a Kubernetes abstraction that represents a group of one or more
application containers (such as Docker), and some shared resources for those
containers. Those resources include:

* Shared storage, as Volumes
* Networking, as a unique cluster IP address
* Information about how to run each container, such as the container image version or specific ports to use

## Node

A node is a worker machine in Kubernetes and may be either a virtual or a
physical machine, depending on the cluster. Each Node is managed by the
Master. A Node can have multiple pods, and the Kubernetes master
automatically handles scheduling the pods across the Nodes in the cluster.
The Master's automatic scheduling takes into account the available resources
on each Node. 

Every Kubernetes Node runs at least:

* Kubelet, a process responsible for communication between the Kubernetes
  Master and the Node; it manages the Pods and the containers running on a
  machine.
* A container runtime (like Docker) responsible for pulling the container image
  from a registry, unpacking the container, and running the application.

## Service

A Service in Kubernetes is an abstraction which defines a logical set of Pods
and a policy by which to access them. Services enable a loose coupling
between dependent Pods. A Service is defined using YAML (preferred) or JSON,
like all Kubernetes objects. The set of Pods targeted by a Service is usually
determined by a LabelSelector (see below for why you might want a Service
without including selector in the spec).