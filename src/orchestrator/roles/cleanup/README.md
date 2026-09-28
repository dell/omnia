# Cleanup role

## Overview

Runs the Orchestrator cleanup engine for the components selected by the
calling cleanup playbook. Each selected component is attempted, and any
failures are collected and reported after the cleanup summary.

## Responsibilities

- Validate the resolved cleanup configuration and execution order.
- Execute each selected component cleanup in priority order.
- Aggregate component results and failures.
- Report a final success or partial-cleanup summary.
- Fail the play when one or more selected components could not be cleaned.

The available component definitions and global cleanup settings are declared
in `config/default_cleanup.yml`. Component selection and confirmation are
handled by the calling cleanup playbooks before this role runs.

## Role variables

The role expects `cleanup_components` and `cleanup_execution_order` to be
defined. Path and state variables used by the cleanup engine are documented in
`vars/main.yml`.

## License

Apache-2.0
