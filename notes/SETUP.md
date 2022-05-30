# SETUP

Setup kubernetes using a simple script. Used as a baseline for automation

## All nodes

```bash
cat <<'SCRIPT' > common.sh
#!/usr/bin/env bash

modprobe br_netfilter

systemctl stop firewalld
systemctl disable firewalld

cat <<EOF > /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://packages.cloud.google.com/yum/repos/kubernetes-el7-x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://packages.cloud.google.com/yum/doc/yum-key.gpg https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg
EOF

dnf config-manager --add-repo=https://download.docker.com/linux/centos/docker-ce.repo
dnf install -y docker-ce
dnf install -y iproute-tc
dnf install -y https://download.docker.com/linux/centos/7/x86_64/stable/Packages/containerd.io-1.2.6-3.3.el7.x86_64.rpm
dnf install -y kubeadm

rm -f /etc/containerd/config.toml

systemctl enable docker
systemctl enable containerd
systemctl enable kubelet
systemctl start docker
systemctl start containerd
systemctl start kubelet
SCRIPT

bash common.sh
```

## Control Plane

```bash
kubeadmin init
```

## Worker Node

Join worker node to the control plane

```bash
kubeadm join 192.168.115.10:6443 --token XXXXXXXXXXXXXXXXXXXXXXX --discovery-token-ca-cert-hash sha256:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

## Networking

Setup Networking

```bash
kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml
```

## Helm

```bash
cd /tmp
wget https://get.helm.sh/helm-v3.9.0-linux-amd64.tar.gz 
tar -zxvf helm*.tar.gz 
cp linux-amd64/helm /usr/local/bin
```