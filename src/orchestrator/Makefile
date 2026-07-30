# Orchestrator Makefile
#
# The playbook handles dependency syncing automatically.
# This Makefile is a convenience wrapper.

.PHONY: run build publish clean

run:
	ansible-playbook orchestrator.yml

build:
	ansible-galaxy collection build --force

publish: build
	ansible-galaxy collection publish omnia-orchestrator-*.tar.gz --api-key $(GALAXY_API_KEY)

clean:
	rm -f omnia-orchestrator-*.tar.gz
