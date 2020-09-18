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


# Installing via RPM because the metadata is broken on these packages.
tempdir=$(mktemp -d -t dockerrpms-XXXXXX)
wget -qP $tempdir https://download.docker.com/linux/centos/7/x86_64/stable/Packages/docker-ce-selinux-17.03.3.ce-1.el7.noarch.rpm
wget -qP $tempdir https://download.docker.com/linux/centos/7/x86_64/stable/Packages/containerd.io-1.2.13-3.2.el7.x86_64.rpm
wget -qP $tempdir https://download.docker.com/linux/centos/7/x86_64/stable/Packages/docker-ce-19.03.9-3.el7.x86_64.rpm
wget -qP $tempdir https://download.docker.com/linux/centos/7/x86_64/stable/Packages/docker-ce-cli-19.03.9-3.el7.x86_64.rpm
rpm -Uv ${tempdir}/*.rpm


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