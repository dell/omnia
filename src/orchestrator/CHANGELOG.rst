==================================
Omnia Orchestrator Release Notes
==================================

.. contents:: Topics

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
