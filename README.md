# kubelab

Build a small Kubernetes test cluster on a single Linux host using KVM/libvirt
and Ansible. VM guests run Ubuntu.

## What this repository builds

Three control-plane nodes, four worker nodes, and two load-balancer nodes
fronting the Kubernetes API server:

| Node              | Role                           |
| ----------------- | ------------------------------ |
| control1.dev.site | Kubernetes control plane       |
| control2.dev.site | Kubernetes control plane       |
| control3.dev.site | Kubernetes control plane       |
| worker1.dev.site  | Kubernetes worker              |
| worker2.dev.site  | Kubernetes worker              |
| worker3.dev.site  | Kubernetes worker              |
| worker4.dev.site  | Kubernetes worker              |
| kubelb1.dev.site  | Load balancer (API server VIP) |
| kubelb2.dev.site  | Load balancer (API server VIP) |

## Installation

### Requirements

- Linux host with KVM support (instructions targeted at Ubuntu 24.04)
- Python 3.8 or newer
- 32 GiB RAM
- 512 GB free disk space

### Clone the repository

```bash
git clone git@github.com:dexterp/kubelab.git
cd kubelab
```

### Install libvirt and QEMU (Ubuntu example)

```bash
sudo apt update
sudo apt install -y libvirt-clients bridge-utils libvirt-daemon \
    libvirt-daemon-system qemu qemu-kvm virt-manager
```

### Start libvirtd

```bash
sudo systemctl start libvirtd
```

### Build and start the VMs

```bash
make vmstart
```

Check progress with `virsh`:

```bash
virsh list --all
```

Example output once all VMs are running:

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

### Configure systemd-resolved to use libvirtd's DNS (optional)

This lets you reach guests by hostname (e.g. `control1.dev.site`) from the
host. Add or update `/etc/systemd/resolved.conf`:

```
[Resolve]
DNS=192.168.115.1
Domains=~dev.site
```

Then restart the resolver:

```bash
sudo systemctl restart systemd-resolved
```

### SSH to a VM guest

Allow a minute after VM startup for libvirtd's dnsmasq to populate DNS. Your
local username and SSH public key are provisioned on each guest automatically,
so you can SSH in with your local username:

```bash
ssh control1.dev.site
# you should get a shell on the remote guest
```

### Install Kubernetes using Ansible

The Kubernetes installation is performed with an Ansible playbook under
`ansible/`:

- `ansible/site.yml` — site playbook
- `ansible/ansible.cfg` — Ansible config
- `ansible/inventory` — inventory file (generated — see `make play` below)
- `ansible/roles/` — role implementations

Run the playbook:

```bash
make play
```

This generates the inventory from `kubelab.yml` and applies the roles for
each node group (`control`, `worker`, `lb`), bringing up containerd,
Kubernetes, Calico networking, and the load balancer.

## Managing this lab

This project uses `make`, Ansible, and libvirt to manage the VM lifecycle.

### Common `Makefile` targets

- `make help` — show help
- `make clean` — reset project state
- `make deps` — install host dependencies
- `make upgrade` — upgrade dependencies
- `make vmstart` — create and start VMs
- `make vmstartpass` - create and start VMs with password authentication
- `make vmshutdown` — shut down VMs
- `make vmremove` — remove VM definitions
- `make play` — run the Ansible playbook
- `make autosync` — rsync project files on change to a target linux host for remote development (requires `fswatch` and `rsync`)

### Libvirt / `virsh` commands

- `virsh list --all` — list domains
- `virsh start <domain>` — start a domain
- `virsh dumpxml <domain>` — show domain XML
- `virsh net-dumpxml kubenet` — show network XML for `kubenet`
