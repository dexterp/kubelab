#!/usr/bin/env bash

umask 077
certsecret=$(kubeadm init phase upload-certs --upload-certs | tail -1)
command="$(kubeadm token create --ttl 2h --print-join-command) --control-plane --certificate-key ${certsecret}"

cat <<EOF
#!/usr/bin/env bash
if [[ ! -f /etc/kubernetes/admin.conf ]]
then
  $command
fi
EOF