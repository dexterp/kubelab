SHELL=/bin/bash

.PHONY: _build _centos8 clean deps _vmcreate vmremove vmstart play

# Python
PYTHON ?= $(shell command -v python3 python|head -n1)
CURUSER ?= $(shell id -un)

#
# Help Script
#
define PRINT_HELP_PYSCRIPT
import re, sys

print("Usage: make <target>\n")
cmds = []
for line in sys.stdin:
    match = re.match(r'^_?([a-zA-Z0-9_-]+):.*?## (.*)$$', line)
    if match:
      target, help = match.groups()
      cmds.append([target, help])
for cmd, help in cmds:
        print("  %s%s%s - %s" % ("\x1b[0001m", cmd, "\x1b[0000m", help))
print("")
endef
export PRINT_HELP_PYSCRIPT

#
# End user targets
#
ifneq (, ${PYTHON})
help: ## Print Help
	@$(PYTHON) -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)
else
help:
	$(error python required for 'make help', executable not found)
endif


clean: ## Reset project to original state
	rm -rf tmp

deps: requirements.txt ## Install dependencies
	@pip install --quiet --requirement requirements.txt

upgrade: ## Install depedency upgrades
	@touch requirements.in
	@$(MAKE) deps

permissions: ## Fix permissions on vmlinuz for non-root users
	@sudo chmod +r /boot/vmlinuz-$(shell uname -r) 
	@sudo setfacl -m u:$(CURUSER):r /boot/vmlinuz-$(shell uname -r)

vmremove: ## Remove virtual guests
	-for host in kubemaster1 kubemaster2 kubemaster3 kuberun1 kuberun2 kuberun3 kuberun4 kubelb1 kubelb2; do \
		virsh -q destroy $${host}; \
	done
	-for host in kubemaster1 kubemaster2 kubemaster3 kuberun1 kuberun2 kuberun3 kuberun4 kubelb1 kubelb2; do \
		virsh -q undefine $${host} --storage ~/.local/share/kubelab/images/$${host}.qcow2; \
	done
	-virsh net-destroy kubenet
	-virsh net-undefine kubenet
	-for host in kubemaster1.dev.site kubemaster2.dev.site kubemaster3.dev.site kuberun1.dev.site kuberun2.dev.site kuberun3.dev.site kuberun4.dev.site kubelb1.dev.site kubelb2.dev.site 192.168.115.10 192.168.115.11 192.168.115.12 192.168.115.13 192.168.115.21 192.168.115.22 192.168.115.23 192.168.115.24 192.168.115.31 192.168.1１5.32; do \
	   ssh-keygen -q -R $$host; \
	done

vmstart: ## Start virtual guests. Create them if they do not exist.
	@test -r /boot/vmlinuz-$(shell uname -r) || $(MAKE) permissions
	scripts/libvirtsetup.py start --config libvirt/manifest/kubenet.yml --net-template libvirt/template/libvirtnetwork.xml.j2 --dom-template libvirt/template/libvirtdomain.xml.j2

vmshutdown: ## Shutdown virtual guests
	scripts/libvirtsetup.py shutdown --config libvirt/manifest/kubenet.yml

play: ## Run ansible playbook on virtual guests
	-cd ansible; ansible-playbook -i inventory site.yml

getconf: ## Copy kubectl config to desktop/laptop
	mkdir -p ~/.kube
	scp kubemaster1:/etc/kubernetes/admin.conf ~/.kube/config.kubelab

#
# file targets
#
tmp:
	@mkdir -p tmp

tmp/.env: scripts/envs.py
	@$(MAKE) tmp
	@scripts/envs.py $@

requirements.txt: requirements.in
	@pip show pip-tools 2>&1 > /dev/null || pip install pip-tools
	pip-compile --output-file=$@ $<
	@-rmdir packer/centos8/output