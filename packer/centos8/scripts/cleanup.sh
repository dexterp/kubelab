#!/usr/bin/env bash

# Remove host ssh keys so they will be regenerated on startup
rm -f /etc/ssh/ssh_host*

# Ensure root has no direct login password
usermod --password '*' root