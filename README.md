# Kubernetes Qemu Setup

WIP: Build a Kubernetes production environment on a single host using KVM 

## Setup

_Requirements_
* Linux host operating system. The instructions at the time of writing are for Ubuntu 20.04
* RAM 32GiB 
* Disk Space 512GB 

_Install Libvirt_
```bash
apt install qemu qemu-kvm libvirt-daemon libvirt-daemon-system libvirt-clients bridge-utils virt-manager
```

_Host resolution using NSS_
This lab requires the Libvirt NSS module to resolve QEMU guests.
More information on the libvirt module can be found at <https://libvirt.org/nss.html>.

```bash
apt install libnss-libvirt

# Edit /etc/nsswitch.conf to relfect the following line
cat /etc/nsswitch.conf
# /etc/nsswitch.conf
hosts:       files libvirt_guest dns
# ...
```

## Makefile targets

* make build - Build packer container runtime images
