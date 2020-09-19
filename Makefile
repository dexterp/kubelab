SHELL=ci/makewrap.sh

.PHONY: build _build_net build_vm _build_ks _build_packer clean deps envs install _install vmcreate _vmcreate vmremove vmstart

build: deps tmp/.env
	# Recursive make calls to interpolate dotenv variables
	$(MAKE) _build_packer
	$(MAKE) _build_net

_build_ks: images/centos8.qcow2

_build_packer: images/container-runtime.qcow2

_build_net:
	(virsh net-info kub-net 2>/dev/null >/dev/null) || virsh net-create libvirt/network/kub-net.xml
	virsh net-autostart kub-net
	virsh net-start kub-net

clean:
	rm -rf tmp
	rm -rf packer/centos{7,8}/output
	rm -rf packer/centos{7,8}/packer_cache
	rm -f packer/centos{7,8}/http/ks.cfg
	rm -f packer/centos{7,8}/config.pkr.hcl
	rm -f packer/centos{7,8}/scripts/creds_sh

deps: requirements.txt
	@pip install --quiet --requirement requirements.txt

#
# VM Guest management
#
vmcreate:
	$(MAKE) _vmcreate

_vmcreate: libvirt/vm/container-runtime.xml images/container-runtime.qcow2
	-virt-clone -n container-runtime1 --original-xml libvirt/vm/container-runtime.xml --file /var/lib/libvirt/images/container-runtime1.qcow2
	-virt-clone -n container-runtime2 --original-xml libvirt/vm/container-runtime.xml --file /var/lib/libvirt/images/container-runtime2.qcow2
	-virt-clone -n container-runtime3 --original-xml libvirt/vm/container-runtime.xml --file /var/lib/libvirt/images/container-runtime3.qcow2
	-virt-clone -n container-runtime4 --original-xml libvirt/vm/container-runtime.xml --file /var/lib/libvirt/images/container-runtime4.qcow2

vmremove:
	-virsh destroy container-runtime1
	-virsh destroy container-runtime2
	-virsh destroy container-runtime3
	-virsh destroy container-runtime4
	-virsh undefine container-runtime1 --storage /var/lib/libvirt/images/container-runtime1.qcow2
	-virsh undefine container-runtime2 --storage /var/lib/libvirt/images/container-runtime2.qcow2
	-virsh undefine container-runtime3 --storage /var/lib/libvirt/images/container-runtime3.qcow2
	-virsh undefine container-runtime4 --storage /var/lib/libvirt/images/container-runtime4.qcow2

vmstart:
	-virsh start container-runtime1
	-virsh start container-runtime2
	-virsh start container-runtime3
	-virsh start container-runtime4

#
# file targets
#
tmp:
	@mkdir -p tmp

tmp/.env: ci/envs.py tmp
	@python ci/envs.py $@

requirements.txt: requirements.in
	@pip show pip-tools 2>&1 > /dev/null || pip install pip-tools
	pip-compile --output-file=$@ $<

libvirt/vm/container-runtime.xml: libvirt/vm/template.j2.xml
	vm_name=template vm_mem_size=4 vm_vcpu_count=8 vm_disk=images/container-runtime.qcow2 j2 $< > $@

images/centos8.qcow2: packer/centos8/ks.pkr.hcl packer/centos8/http/ks.cfg
	@mkdir -p images
	-rm -rf packer/centos8/output_ks
	cd packer/centos8; packer build -on-error=$(PACKERONERROR) ks.pkr.hcl
	mv packer/centos8/output_ks/centos8-x86_64 images/centos8.qcow2
	@-rm -rf output_ks

images/container-runtime.qcow2: packer/centos8/config.pkr.hcl packer/centos8/http/ks.cfg $(wildcard packer/centos8/scripts/*) $(wildcard packer/centos8/network/*) $(wildcard packer/centos8/vm/*) packer/centos8/scripts/creds_sh
	@mkdir -p images
	-rm -rf packer/centos8/output
	cd packer/centos8; packer build -on-error=$(PACKERONERROR) config.pkr.hcl
	mv packer/centos8/output/kubernetes-centos8-x86_64 images/container-runtime.qcow2
	@-rm -rf output

%: %.j2
	j2 $< > $@
