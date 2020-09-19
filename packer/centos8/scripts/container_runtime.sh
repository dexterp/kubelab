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

# Install *.repo file
cat > /etc/yum.repos.d/docker-ce.repo <<'EOF'
[docker-ce-stable]
name=Docker CE Stable - $basearch
baseurl=https://download.docker.com/linux/centos/8/$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://download.docker.com/linux/centos/gpg
EOF

dnf install -y containerd.io docker-ce docker-ce-cli


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