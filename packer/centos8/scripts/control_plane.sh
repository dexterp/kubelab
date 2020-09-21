#!/usr/bin/env bash

perl -pi -e 's/^SELINUX=.*/SELINUX=permissive/g' /etc/sysconfig/selinux

useradd -r kubernetes -u 500 -m

systemctl disable firewalld
systemctl enable kubelet