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


# USE make build - see wrapper and the end of this Makefile
_build: deps ## Build and start virtual guests
	$(MAKE) _vmcreate

clean: ## Reset project to original state
	rm -rf tmp
	rm -rf packer/centos{7,8}/output
	rm -rf packer/centos{7,8}/packer_cache
	rm -rf packer/centos{7,8}/images
	rm -f packer/centos{7,8}/centos{7,8}.pkr.hcl
	rm -f packer/centos{7,8}/http/ks.cfg
	rm -f libvirt/vm/kube*.xml

deps: requirements.txt ## Install dependencies
	@pip install --quiet --requirement requirements.txt

upgrade: ## Install depedency upgrades
	@touch requirements.in
	@$(MAKE) deps

#
# VM Guest management
#

_vmcreate: _qemu ## Create virtual guests

.PHONY: _centos7
_centos7: packer/centos7/images/centos7.qcow2

.PHONY: _centos8
_centos8: packer/centos8/images/centos8.qcow2 ## Build Cenots8 Image

.PHONY: _qemu
_qemu: _centos8 libvirt/vm/kuberun.xml libvirt/vm/kubemaster.xml
	-virsh net-define libvirt/network/kubenet.xml
	-for host in kuberun1 kuberun2 kuberun3 kuberun4; do \
		virt-clone -n $${host} --original-xml libvirt/vm/kuberun.xml --file /var/lib/libvirt/images/$${host}.qcow2; \
	done
	-virt-clone -n kubemaster1 --original-xml libvirt/vm/kubemaster.xml --file /var/lib/libvirt/images/kubemaster1.qcow2
	-scripts/setstaticip.py kubemaster1 kubenet 192.168.115.10
	-scripts/setstaticip.py kuberun1 kubenet 192.168.115.11
	-scripts/setstaticip.py kuberun2 kubenet 192.168.115.12
	-scripts/setstaticip.py kuberun3 kubenet 192.168.115.13
	-scripts/setstaticip.py kuberun4 kubenet 192.168.115.14
	-virsh net-start kubenet
	$(MAKE) vmstart

vmremove: ## Remove virtual guests
	-for host in kubemaster1 kuberun1 kuberun2 kuberun3 kuberun4; do \
		virsh destroy $${host}; \
	done
	-for host in kubemaster1 kuberun1 kuberun2 kuberun3 kuberun4; do \
		virsh undefine $${host} --storage /var/lib/libvirt/images/$${host}.qcow2; \
	done
	-virsh net-destroy kubenet
	-virsh net-undefine kubenet
	-for host in kubemaster1 kuberun1 kuberun2 kuberun3 kuberun4 192.168.115.10 192.168.115.11 192.168.115.12 192.168.115.13 192.168.115.14; do \
	   ssh-keygen -R $$host; \
	done

vmstart: ## Start virtual guests
	-virsh net-start kubenet
	-virsh start kuberun1
	-virsh start kuberun2
	-virsh start kuberun3
	-virsh start kuberun4
	-virsh start kubemaster1

vmshutdown: ## Shutdown virtual guests
	-virsh shutdown kuberun1
	-virsh shutdown kuberun2
	-virsh shutdown kuberun3
	-virsh shutdown kuberun4
	-virsh shutdown kubemaster1

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
	@test -x scripts/envs.py || chmod +x scripts/envs.py
	@scripts/envs.py $@

requirements.txt: requirements.in
	@pip show pip-tools 2>&1 > /dev/null || pip install pip-tools
	pip-compile --output-file=$@ $<

libvirt/vm/kuberun.xml: libvirt/vm/template.j2.xml
	vm_name=template vm_mem_size=4 vm_vcpu_count=8 vm_disk=packer/centos8/images/centos8.qcow2 j2 $< > $@

libvirt/vm/kubemaster.xml: libvirt/vm/template.j2.xml
	vm_name=template vm_mem_size=2 vm_vcpu_count=4 vm_disk=packer/centos8/images/centos8.qcow2 j2 $< > $@

packer/centos7/images/sha256sums.txt: $(wildcard packer/centos7/images/*.qcow2)
	cd packer/centos7/images; sha256sum -b *.qcow2 > sha256sums.txt

packer/centos7/images/centos7.qcow2: packer/centos7/centos7.pkr.hcl packer/centos7/http/ks.cfg
	@mkdir -p packer/centos7/images
	@-rmdir packer/centos7/output
	cd packer/centos7; packer build -on-error=$(PACKERONERROR) centos7.pkr.hcl
	mv packer/centos7/output/centos7 packer/centos7/images/centos7.qcow2
	$(MAKE) packer/centos7/images/sha256sums.txt
	@-rmdir packer/centos7/output

packer/centos8/images/sha256sums.txt: $(wildcard packer/centos8/images/*.qcow2)
	cd packer/centos8/images; sha256sum -b *.qcow2 > sha256sums.txt

packer/centos8/images/centos8.qcow2: packer/centos8/centos8.pkr.hcl packer/centos8/http/ks.cfg
	@mkdir -p packer/centos8/images
	@-rmdir packer/centos8/output
	cd packer/centos8; packer build -on-error=$(PACKERONERROR) centos8.pkr.hcl
	mv packer/centos8/output/centos8 packer/centos8/images/centos8.qcow2
	$(MAKE) packer/centos8/images/sha256sums.txt
	@-rmdir packer/centos8/output

%: %.j2
	j2 $< > $@

%: %.envsubst
	envsubst < $< > $@

#
# make wrapper - Execute any target target prefixed with a underscore.
# EG 'make vmcreate' will result in the execution of 'make _vmcreate' 
#
%:
	@test -x scripts/dotenv.sh || chmod +x scripts/dotenv.sh
	@egrep -q '^_$@:' Makefile && $(MAKE) tmp/.env && scripts/dotenv.sh $(MAKE) _$@
