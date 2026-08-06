#!/usr/bin/env bash

umask 077

outfile=$1
tlssecret=$(kubeadm init phase upload-certs --upload-certs | tail -1)
command="$(kubeadm token create --ttl 2h --print-join-command) --control-plane --certificate-key ${tlssecret} --patches /var/local/ansible/files/kubeadm-init-patches"

tmpfile=$(mktemp /tmp/kube-add-control.XXXXXX)

cat > $tmpfile <<EOF
#!/usr/bin/env bash
if [[ ! -f /etc/kubernetes/admin.conf ]]
then
  $command
fi
EOF

mv $tmpfile $outfile

at now + 1hour <<< "rm -f ${outfile}"