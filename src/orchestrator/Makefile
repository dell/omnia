# Orchestrator Makefile
#
# The playbook handles dependency syncing automatically.
# This Makefile is a convenience wrapper.

.PHONY: run clean

run:
	ansible-playbook orchestrator.yml

clean:
	rm -rf common/
