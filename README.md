# Kubernetes QEMU Installation

Build a small Kubernetes test environment on a single host using KVM/libvirt.

What this repository builds

| Node     | Description            |
| -------- | ---------------------- |
| control1 | Kubernetes Master Node |
| control2 | Kubernetes Master Node |
| control3 | Kubernetes Master Node |
| worker1  | Kubernetes runtime     |
| worker2  | Kubernetes runtime     |
| worker3  | Kubernetes runtime     |
| worker4  | Kubernetes runtime     |
| kubelb1  | Load Balancer          |
| kubelb2  | Load Balancer          |

## Installation

Requirements

- Linux host with KVM support (instructions targeted at Ubuntu 24.04)
- Python 3.8 or newer
- RAM: 32 GiB
- Disk space: 512 GB

Clone the repository

```bash
git clone git@github.com:dexterp/kubelab.git
cd kubelab
```

Install libvirt and QEMU (Ubuntu example)

```bash
sudo apt update
sudo apt install -y libvirt-clients bridge-utils libvirt-daemon \
    libvirt-daemon-system qemu qemu-kvm virt-manager
```

Start libvirtd

```bash
sudo systemctl start libvirtd
```

Build and start the VMs

```bash
make vmstart
```

Using `virsh` to list VMs

```bash
virsh list --all
```

Example running VMs

```
 Id   Name          State
-----------------------------
 6    control1      running
 7    control2      running
 8    control3      running
 9    worker1       running
 10   worker2       running
 11   worker3       running
 12   worker4       running
 13   kubelb1       running
 14   kubelb2       running
```

Configure systemd-resolved to use libvirtd's DNS (optional)

Add or update `/etc/systemd/resolved.conf` with the following:

```
[Resolve]
DNS=192.168.115.1
Domains=~dev.site
```

Then restart the resolver:

```bash
sudo systemctl restart systemd-resolved
```

SSH to a VM guest

Allow a minute after VM startup for libvirtd's dnsmasq to populate DNS. The
user's public key is installed in the user account on each guest so you can SSH
using your local username which was created on the vm guests. The public key was
added to the user account.

```bash
ssh control1.dev.site
# you should get a shell on the remote guest
```

Install Kubernetes using Ansible

TODO: update Ansible for Ubuntu. Ansible is currently disabled until it is
converted.

The Kubernetes installation is performed with an Ansible playbook under
`ansible/`.

- `ansible/site.yml` — site playbook
- `ansible/ansible.cfg` — Ansible config
- `ansible/inventory` — inventory file
- `ansible/roles/` — role implementations

Note: The roles may require conversion or adjustments depending on target
distribution.

Run the playbook

```bash
make play
```

## Managing this lab

This project uses `make`, Ansible and libvirt to manage the VM lifecycle.

Common `Makefile` targets

- `make help` — show help
- `make clean` — reset project state
- `make deps` — install host dependencies
- `make upgrade` — upgrade dependencies
- `make vmstart` — create and start VMs
- `make vmshutdown` — shut down VMs
- `make vmremove` — remove VM definitions
- `make play` — run the Ansible playbook
- `make permissions` — fix vmlinuz permissions for non-root users
- `make autosync` — rsync files on change (requires `fswatch` and `rsync`)

Libvirt / `virsh` commands

- `virsh list --all` — list domains
- `virsh start <domain>` — start a domain
- `virsh dumpxml <domain>` — show domain XML
- `virsh net-dumpxml kubenet` — show network XML for `kubenet`
