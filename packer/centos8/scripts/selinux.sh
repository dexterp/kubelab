#!/usr/bin/env bash

sed -i 's/^SELINUX=enforcing$/SELINUX=permissive/' /etc/selinux.config