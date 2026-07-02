#!/usr/bin/env bash



#
# Cleanup
#
rm -f /etc/machine-id
rm -f /etc/ssh/ssh_host_*

find /var/log -type f -exec truncate -s 0 {} \;
truncate -s 0 /root/.bash_history

rm -f /etc/sudoers.d/packer
rm -f /tmp/provisioner.sh