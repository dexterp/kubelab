SHELL=/bin/bash

.PHONY: _build _centos8 clean deps _vmcreate vmremove vmstart play

# Python
PYTHON ?= $(shell command -v python3 python|head -n1)

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
	rm -rf packer/ubuntu-26-04-lts/images/*
	rm -rf packer/ubuntu-26-04-lts/output/*
	rm -rf packer/ubuntu-26-04-lts/http/user-data
	rm -rf packer/ubuntu-26-04-lts/ubuntu26-04-lts.pkr.hcl

deps: requirements.txt ## Install dependencies
	@pip install --quiet --requirement requirements.txt

upgrade: ## Install depedency upgrades
	@touch requirements.in
	@$(MAKE) deps

.PHONY: images
images: packer/ubuntu-26-04-lts/images/ubuntu-26-04-lts.qcow2 ## Build machine image

.PHONY: template
template: packer/ubuntu-26-04-lts/ubuntu26-04-lts.pkr.hcl packer/ubuntu-26-04-lts/http/user-data ## Build packer templates

vmremove: ## Remove virtual guests
	-for host in kubemaster1 kubemaster2 kubemaster3 kuberun1 kuberun2 kuberun3 kuberun4 kubelb1 kubelb2; do \
		virsh -q destroy $${host}; \
	done
	-for host in kubemaster1 kubemaster2 kubemaster3 kuberun1 kuberun2 kuberun3 kuberun4 kubelb1 kubelb2; do \
		virsh -q undefine $${host} --storage ~/.local/share/kubelab/images/$${host}.qcow2; \
	done
	-virsh net-destroy kubenet
	-virsh net-undefine kubenet
	-for host in kubemaster1 kubemaster2 kubemaster3 kuberun1 kuberun2 kuberun3 kuberun4 kubelb1 kubelb2 192.168.115.10 192.168.115.11 192.168.115.12 192.168.115.13 192.168.115.21 192.168.115.22 192.168.115.23 192.168.115.24 192.168.115.31 192.168.115.32; do \
	   ssh-keygen -q -R $$host; \
	done

vmstart: ## Start virtual guests
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

packer/ubuntu-26-04-lts/http/user-data: packer/ubuntu-26-04-lts/http/user-data.envsubst tmp/.env
	@set -a; source tmp/.env; set +a; envsubst < $< > $@

packer/ubuntu-26-04-lts/ubuntu26-04-lts.pkr.hcl: packer/ubuntu-26-04-lts/ubuntu26-04-lts.pkr.hcl.envsubst tmp/.env
	@set -a; source tmp/.env; set +a; envsubst < $< > $@

requirements.txt: requirements.in
	@pip show pip-tools 2>&1 > /dev/null || pip install pip-tools
	pip-compile --output-file=$@ $<
	@-rmdir packer/centos8/output

packer/ubuntu-26-04-lts/images/ubuntu-26-04-lts.qcow2: packer/ubuntu-26-04-lts/ubuntu26-04-lts.pkr.hcl packer/ubuntu-26-04-lts/http/user-data packer/ubuntu-26-04-lts/output/ubuntu26_04_lts
	@mkdir -p packer/ubuntu-26-04-lts/images
	cp packer/ubuntu-26-04-lts/output/ubuntu26_04_lts packer/ubuntu-26-04-lts/images/ubuntu-26-04-lts.qcow2
	cd packer/ubuntu-26-04-lts/images; sha256sum -b ubuntu-26-04-lts.qcow2 > sha256sums.txt

packer/ubuntu-26-04-lts/output/ubuntu26_04_lts:
	@-rmdir packer/ubuntu-26-04-lts/output
	cd packer/ubuntu-26-04-lts; packer build ubuntu26-04-lts.pkr.hcl