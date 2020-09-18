SHELL=ci/makewrap.sh

.PHONY: build _build_net _build_packer _build_$(BUILDOS) clean deps envs install _install

hello_world:
	env

build: deps tmp/.env
	$(MAKE) _build_packer
	$(MAKE) _build_net

_build_packer: packer/$(BUILDOS)/config.pkr.hcl packer/$(BUILDOS)/http/ks.cfg packer/$(BUILDOS)/scripts/creds_sh
	cd packer/$(BUILDOS); test -d output || packer build -on-error=$(PACKERONERROR) config.pkr.hcl

_build_net:
	(virsh net-info kub-net 2>/dev/null >/dev/null) || virsh net-create libvirt/network/kub-net.xml

clean:
	rm -rf tmp
	rm -rf packer/centos{7,8}/output
	rm -rf packer/centos{7,8}/packer_cache
	rm -f packer/centos{7,8}/http/ks.cfg
	rm -f packer/centos{7,8}/config.pkr.hcl
	rm -f packer/centos{7,8}/scripts/creds_sh

deps: requirements.txt
	@pip install --quiet --requirement requirements.txt

install:
	$(MAKE) _install

_install:
	install -C -m 644 packer/$(BUILDOS)/output/kubernetes-$(BUILDOS)-x86_64 $(VMIMAGEDIR)/kubernetes-$(BUILDOS)-x86_64.qcow2

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

%: %.j2
	j2 $< > $@
