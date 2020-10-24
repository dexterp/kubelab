# Kubernetes Qemu Installation

Build a Kubernetes production environment on a single host using KVM 

_What will be built?_
| Node        | Description            |
|-------------|------------------------|
| kubemaster1 | Kubernetes Master Node |
| kuberun1    | Kubernetes runtime     |
| kuberun2    | Kubernetes runtime     |
| kuberun3    | Kubernetes runtime     |
| kuberun4    | Kubernetes runtime     |

## Installation

_Requirements_
* Linux host operating system. The instructions at the time of writing are for Ubuntu 20.04
* Python 3. This lab will start 
* RAM 32GiB 
* Disk Space 512GB 

_Download this repository_
```bash
$ git clone git@github.com:dexterp/kubelab.git
$ cd kubelab
```

_Install Libvirt_
```bash
$ sudo apt install libvirt-clients bridge-utils libvirt-daemon \
                   libvirt-daemon-system qemu qemu-kvmt virt-manager
```

_Start Libvrtd_
```bash
$ sudo systemctl start libvirtd
```

_Build and start VMs_

```bash
$ make build
```

_Using virsh to list vms_

Once build is complete you can manage the Virtual Machines using virsh.

```bash
$ virsh list

 Id   Name          State
-----------------------------
 6    kuberun1      running
 7    kuberun2      running
 8    kuberun3      running
 9    kuberun4      running
 10   kubemaster1   running
```

_Host resolution using NSS_

In order to resolve VM guest hostnames libvirt has a NSS module which will
automatically detect and resolve hostnames using client resolver. More
information about libvirt NSS can be found at <https://libvirt.org/nss.html>.

To resolve hostnames, install libvirt NSS .
```bash
$ sudo apt install libnss-libvirt

# Edit /etc/nsswitch.conf to relfect the following line
$ cat /etc/nsswitch.conf
hosts:       files libvirt_guest dns
...
```

_ssh to a VM guest_

The VMs need a minute or more after starting to allow NSS libvirtd time to pick up the nodes.
Once they have appeared one can ssh directly to the host using ones username or the root account.
The $USER(s) public key is added to both the root account and the $USER account on each VM guest.

SSH to the kubernetes master to test that connectivity is working
```bash
$ ssh kubemaster1

[root@kubemaster1 ~]# 
```

_Install Kubernetes Using Ansible_

The installation of Kubernetes is installed using an ansible playbook. The Ansible playbook is under the directory `ansible/`

* `ansible/site.yml` - Ansible site configuration
* `ansible/ansible.cfg` - Ansible configuration file
* `ansible/inventory` - Ansible inventory
* `ansible/roles/**` - Ansible roles

Run the following command to install Kubernetes using the Ansible playbook...
```bash
make runplaybook
```

# Managing this lab 

This lab uses make, ansible, libvirt and other tools to manage the lifecycle
of VMs in this lab. This section provides some help on these tools.

## Makefile targets

* `make help`        - Print help information
* `make build`       - Build packer container runtime images
* `make vmcreate`    - Create VMs
* `make vmstart`     - Start VMs
* `make runplaybook` - Run Ansible Playbook
* `make vmremove`    - Remove VMs

## Libvirtd commands

As the VMs are managed by Libvirtd the `virsh` cli can be used to manage the VMs directly.

Some common commands.

* `virsh list`           - List networks  
* `virsh start <domain>` - Start a domain (VM)