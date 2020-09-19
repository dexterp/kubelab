#!/usr/bin/env bash

# (Install Docker CE)
## Set up the repository
### Install required packages
dnf install -y device-mapper-persistent-data lvm2


## Add EPEL
dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
dnf config-manager --set-enabled PowerTools

dnf install -y dnf-utils device-mapper-persistent-data fuse-overlayfs
dnf install -y libcgroup libcgroup-tools
dnf install -y container-selinux

# Install Docker .repo file
cat > /etc/yum.repos.d/docker-ce.repo <<'EOF'
[docker-ce-stable]
name=Docker CE Stable - $basearch
baseurl=https://download.docker.com/linux/centos/8/$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://download.docker.com/linux/centos/gpg
EOF

dnf install -y containerd.io docker-ce docker-ce-cli

# Install CRI-O .repo file
curl -L -o /etc/yum.repos.d/devel:kubic:libcontainers:stable.repo \
  https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/CentOS_8/devel:kubic:libcontainers:stable.repo

curl -L -o /etc/yum.repos.d/devel:kubic:libcontainers:stable:cri-o:1.19.repo \
  https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable:/cri-o:/1.19/CentOS_8/devel:kubic:libcontainers:stable:cri-o:1.19.repo

dnf install -y cri-o

mkdir -p /etc/docker

# Set up the Docker daemon
cat > /etc/docker/daemon.json <<EOF
{
  "exec-opts": ["native.cgroupdriver=systemd"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m"
  },
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.override_kernel_check=true"
  ]
}
EOF

mkdir -p /etc/systemd/system/docker.service.d

## Configure containerd
mkdir -p /etc/containerd
mv /etc/containerd/config.toml{,.bak}
containerd config default > /etc/containerd/config.toml

perl -pi -e 's/systemd_cgroup\s*=.*/systemd_cgroup = true/' /etc/containerd/config.toml

cat > /etc/modules-load.d/kubernetes-cri.conf <<EOF
overlay
br_netfilter
EOF

cat > /etc/sysctl.d/99-kubernetes-cri.conf <<EOF
net.bridge.bridge-nf-call-iptables  = 1
net.ipv4.ip_forward                 = 1
net.bridge.bridge-nf-call-ip6tables = 1
EOF

systemctl daemon-reload
systemctl enable docker
systemctl enable crio
systemctl enable containerd