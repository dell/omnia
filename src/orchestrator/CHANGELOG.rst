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

Breaking Changes
---------------

- Renamed ``phone_home`` timing and verification controls to ``node_registration`` throughout PXE provisioning workflow.
  - Role: ``verify_phone_home`` → ``verify_node_registration``
  - Variables: ``enable_phone_home`` → ``enable_node_registration``, etc.
  - Legacy ``phone_home_*`` variables supported with deprecation warning
  - Node completion is verified directly through SSH, boot freshness, and cloud-init status

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
