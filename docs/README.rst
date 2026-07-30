Omnia Documentation
-------------------

**Omnia** is an open source project hosted on `GitHub <https://github.com/dell/omnia>`_.

This directory contains **generic** Omnia documentation shared across all domains.
Domain-specific docs live inside each domain (e.g. ``src/image_build_manager/docs/``).
Per-script documentation lives in ``src/main/docs/``.

::

  docs/
  ├── code-style/                   Code style guides (Ansible, Python, Jinja2, test automation)
  ├── design/                       Cross-domain design documents
  │   ├── domain-integration.md
  │   ├── omnia-domain-repo-design.md
  │   └── test-automation-design.md
  └── logos/                        Omnia branding assets

  src/main/docs/
  ├── omnia-env.md                  Environment variable reference
  ├── omnia-setup.md                Setup script (omnia.sh) documentation
  └── omnia-cli.md                  CLI (omnia-cli) documentation

Environment Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

Environment variables are configured in ``src/main/omnia.env`` and installed
system-wide by ``omnia.sh --setup-venv``:

- ``/etc/omnia/omnia.env`` — persistent system-wide copy
- ``/etc/profile.d/omnia-env.sh`` — auto-sources the env on every login shell

After setup, all scripts, playbooks, and new shells automatically have access
to Omnia environment variables. No manual sourcing is required.
