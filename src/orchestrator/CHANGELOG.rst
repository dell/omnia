==================================
Omnia Orchestrator Release Notes
==================================

.. contents:: Topics

v2.3.0
======

Release Summary
---------------

Bug fixes for PXE boot, node-registration verification, provisioning report,
inventory generation, and galaxy version alignment.

Bug Fixes
---------

- Removed the invalid generic cloud-init phone-home fragment; Metadata Service reserves that endpoint for optional WireGuard bootstrap peer removal.
- Updated Boot Service parameters to use ``ds=nocloud`` and disabled unsupported root filesystem resize on the live overlay image.
- Made the Slurm tracking mount explicit and changed controller-marker waits from unbounded loops to bounded failures.
- Fixed stale node-registration detection by verifying node boot time via /proc/uptime (#461).
- Fixed ``failed_nodes.json`` race condition in PXE failure collection (#460).
- Fixed provisioning report comparing GROUP_NAMEs against xnames (#458).
- Added pre-check for missing ``configs_vars.yaml`` with clear error (#450).
- Added custom inventory support for ``pxeboot.yml`` (#432).
- Galaxy version set to 2.3.0 across all domains (#449).

Features
--------

- Added ownership-aware Metadata Service reconciliation and persistent per-node metadata application status.
- Added persistent Service Tag-to-XNAME identity resolution through native SMD Hardware Inventory.
- Added the CA-verified ``openchami_reconcile`` Ansible module for SMD and OpenCHAMI reconciliation.
- Provision, validation, and PXE workflows consume only SMD-resolved identities; PXE mappings do not contain XNAME values.
- Metadata Service resources are updated in place through CA-verified APIs, with safe stale-group cleanup.
- Provisioning-password hashes are stable for each project and cluster, with plaintext supplied to OpenSSL over standard input.
- Reorganized Orchestrator documentation into focused lowercase architecture, identity, troubleshooting, contract, and container guides.

Breaking Changes
---------------

- Node-registration timing and verification use the
  ``enable_node_registration``, ``node_registration_pause_minutes``,
  ``node_registration_retries``, and ``node_registration_delay`` controls.
- Node completion is verified directly through SSH, boot freshness, and cloud-init status.

v2.2.0
======

Release Summary
---------------

Initial Ansible Galaxy collection release of the Omnia Orchestrator domain.

Major Changes
-------------

- Converted orchestrator domain to Ansible Galaxy collection (``omnia.orchestrator``).
- Restructured ``library/`` to ``plugins/modules/`` and ``plugins/module_utils/``.
- Restructured ``callback_plugins/`` to ``plugins/callback/``.
- Updated all module calls and role references to use FQCN.
- Updated Python ``module_utils`` imports to collection paths.
- Added ``DOCUMENTATION`` docstrings to all modules.
- Added ``meta/main.yml`` and ``README.md`` to all roles.
