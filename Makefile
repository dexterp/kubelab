SHELL=/bin/bash

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

upgrade: ## Install dependency upgrades
	@touch requirements.in
	@$(MAKE) deps

vmstart: ## Start virtual guests. Create them if they do not exist.
	@test -r /boot/vmlinuz-$(shell uname -r) || $(MAKE) permissions
	scripts/libvirtsetup.py start --config kubelab.yml --net-template libvirt/template/libvirtnetwork.xml.j2 --dom-template libvirt/template/libvirtdomain.xml.j2

vmstartpass: tmp/password ## Start vms with a root password for debugging
	scripts/libvirtsetup.py start --config kubelab.yml --net-template libvirt/template/libvirtnetwork.xml.j2 --dom-template libvirt/template/libvirtdomain.xml.j2 --password tmp/password

vmshutdown: ## Shutdown virtual guests
	scripts/libvirtsetup.py shutdown --config kubelab.yml

vmremove: ## Remove virtual guests
	-scripts/libvirtsetup.py remove --config kubelab.yml

play: ansible/inventory vmstart ## Run ansible playbook on virtual guests
	@cd ansible && ansible-playbook -i inventory site.yml

permissions: # Fix permissions on vmlinuz for non-root users
	@sudo chmod g+r /boot/vmlinuz-$(shell uname -r) 
	@sudo setfacl -m u:$(CURUSER):r /boot/vmlinuz-$(shell uname -r)

autosync: ## Automatically rsync files to a remote host when they change. Requires fswatch and rsync.
	@test -f rsyncdest.txt || (read -p "Enter the destination path for rsync (e.g. user@host:/path/to/dir): " dest; echo $$dest > rsyncdest.txt)
	@test -f rsyncdest.txt || (echo "rsyncdest.txt not found. Please create it with the destination path for rsync." && exit 1)	
	rsync -avz --exclude-from=.rsyncignore . $$(cat rsyncdest.txt)
	fswatch -o . | xargs -n1 -I{} rsync -avz --exclude-from=.rsyncignore . $$(cat rsyncdest.txt)


#
# file targets
#
tmp:
	@mkdir -p tmp

tmp/password:
	@read -rsp "Enter Password: " password && echo $$password > tmp/password

requirements.txt: requirements.in
	@pip show pip-tools 2>&1 > /dev/null || pip install pip-tools
	pip-compile --output-file=$@ $<

ansible/inventory: kubelab.yml
	scripts/ansiblesetup.py inventory --config kubelab.yml $@