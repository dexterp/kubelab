# Kubernetes Qemu Setup

Build a Kubernetes production environment on a single host using KVM 

_What will be built?_
| Node        | Description            |
|-------------|------------------------|
| kubemaster1 | Kubernetes Master Node |
| kuberun1    | Kubernetes runtime     |
| kuberun2    | Kubernetes runtime     |
| kuberun3    | Kubernetes runtime     |
| kuberun4    | Kubernetes runtime     |

## Setup

_Requirements_
* Linux host operating system. The instructions at the time of writing are for Ubuntu 20.04
* Python 3. This lab will start 
* RAM 32GiB 
* Disk Space 512GB 

_Download this repository_
```bash
git clone 
cd kubelab
```

_Install Libvirt_
```bash
sudo apt install qemu qemu-kvm libvirt-daemon libvirt-daemon-system libvirt-clients bridge-utils virt-manager
```

_Start Libvrtd_
```bash
sudo systemctl start libvirtd
```

_Build VMs_
```bash
make vmcreate
```

_Start VMs_
```bash
make vmstart
```

_Host resolution using NSS_
This lab requires the Libvirt NSS module to resolve QEMU guests.
More information on the libvirt module can be found at <https://libvirt.org/nss.html>.

Adding the following will allow resolution of the hostname.
```bash
sudo apt install libnss-libvirt

# Edit /etc/nsswitch.conf to relfect the following line
cat /etc/nsswitch.conf
# /etc/nsswitch.conf
hosts:       files libvirt_guest dns
# ...
```

_Check ssh connection_

The VMs need a minute or more after starting to allow NSS libvirtd time to pick up the nodes.
Once they have appeared one can ssh directly to the host using ones username or the root account.
The $USER(s) public key is added to both the root account or $USER.

SSH to the kubernetes master to test that connectivity is working
```bash
ssh kubemaster1
```

## Makefile targets

* `make build`      - Build packer container runtime images
* `make vmcreate`   - Create VMs
* `make vmstart`    - Start VMs
* `make runansible` - Run Ansible 
* `make vmremove`   - Remove VMs

## Libvirtd commands

As the VMs are managed by Libvirtd the `virsh` cli can be used to manage the VMs directly.

Some common commands.

* `virsh list`           - List networks  
* `virsh start <domain>` - Start a domain (VM)