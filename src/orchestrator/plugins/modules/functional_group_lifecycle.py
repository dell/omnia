#!/usr/bin/python
# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=import-error,no-name-in-module,too-many-branches,too-many-statements
"""Ansible module for flexible functional group lifecycle mutation safety (ER-ORCH-009)."""

from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.functional_group_lifecycle import (
    BoundedRecoveryManager,
    LifecycleError,
    LifecyclePlanner,
    LockContentionError,
    NodeNotEmptiedError,
    OwnershipAmbiguityError,
    ProjectLock,
    RecoveryRequiredError,
    TransitionJournal,
)

DOCUMENTATION = r'''
---
module: functional_group_lifecycle
short_description: Manage flexible functional group lifecycle mutation safety
version_added: "2.3.0"
description:
  - Manages project-scoped mutation locking, transition journaling, and bounded recovery.
  - Plans add, remove, and configure operations with node-emptiness and ownership checks.
options:
  action:
    description: Lifecycle action to execute.
    type: str
    required: true
    choices:
      - acquire_lock
      - release_lock
      - start_journal
      - record_stage
      - finish_journal
      - plan_add
      - plan_remove
      - plan_configure
      - evaluate_recovery
  project_name:
    description: Orchestrator project name.
    type: str
    default: "default"
  target_group:
    description: Exact target flexible group name (starts with fg_).
    type: str
  operation:
    description: Lifecycle operation (add, remove, configure).
    type: str
    choices: [add, remove, configure]
  run_id:
    description: Unique run identifier.
    type: str
  state_dir:
    description: Directory to store project lock and journal artifacts.
    type: str
    required: true
  mapped_nodes:
    description: List of mapped nodes for the target group (for remove precheck).
    type: list
    elements: raw
    default: []
  all_functional_groups:
    description: All functional groups in active mapping.
    type: list
    elements: dict
    default: []
  ownership_evidence:
    description: Ownership proof for records targeted by remove.
    type: dict
    default: {}
  planned_stages:
    description: List of planned stages for journal initialization.
    type: list
    elements: str
    default: []
  stage:
    description: Stage name for record_stage.
    type: str
  stage_status:
    description: Stage status (attempted, verified, failed).
    type: str
  terminal_result:
    description: Terminal result for finish_journal.
    type: str
    choices: [succeeded, noop, failed, blocked, recovery_required]
  configure_scope:
    description: Configuration scope (both, boot, cloud_init).
    type: str
    default: "both"
    choices: [both, boot, cloud_init]
  force_recovery:
    description: Allow recovering an inactive prior owner's lock.
    type: bool
    default: false
author:
  - Dell Omnia Team
'''

EXAMPLES = r'''
- name: Acquire project mutation lock
  omnia.orchestrator.functional_group_lifecycle:
    action: acquire_lock
    project_name: cluster_a
    operation: add
    target_group: fg_web_rhel_10_2_x86_64
    run_id: "1731800000"
    state_dir: "/opt/omnia/orchestrator"
'''

RETURN = r'''
lock_data:
  description: Metadata of acquired lock.
  type: dict
  returned: when action is acquire_lock
plan:
  description: Planned stages and no-op status.
  type: dict
  returned: when action is plan_*
journal:
  description: Current journal data.
  type: dict
  returned: when action is start_journal, record_stage, or finish_journal
'''


def main() -> None:
    """Run the Ansible module."""
    module = AnsibleModule(
        argument_spec={
            "action": {
                "type": "str",
                "required": True,
                "choices": [
                    "acquire_lock",
                    "release_lock",
                    "start_journal",
                    "record_stage",
                    "finish_journal",
                    "plan_add",
                    "plan_remove",
                    "plan_configure",
                    "evaluate_recovery",
                ],
            },
            "project_name": {"type": "str", "default": "default"},
            "target_group": {"type": "str"},
            "operation": {"type": "str", "choices": ["add", "remove", "configure"]},
            "run_id": {"type": "str"},
            "state_dir": {"type": "str", "required": True},
            "mapped_nodes": {"type": "list", "elements": "raw", "default": []},
            "all_functional_groups": {"type": "list", "elements": "dict", "default": []},
            "ownership_evidence": {"type": "dict", "default": {}},
            "planned_stages": {"type": "list", "elements": "str", "default": []},
            "stage": {"type": "str"},
            "stage_status": {"type": "str"},
            "terminal_result": {
                "type": "str",
                "choices": ["succeeded", "noop", "failed", "blocked", "recovery_required"],
            },
            "configure_scope": {
                "type": "str",
                "default": "both",
                "choices": ["both", "boot", "cloud_init"],
            },
            "force_recovery": {"type": "bool", "default": False},
        },
        supports_check_mode=True,
    )

    action = module.params["action"]
    state_dir = Path(module.params["state_dir"])
    lock_file = state_dir / ".functional_group_mutation.lock"
    journal_file = state_dir / ".functional_group_journal.json"

    lock = ProjectLock(lock_file)
    journal = TransitionJournal(journal_file)

    try:
        if action == "acquire_lock":
            lock_data = lock.acquire(
                project_name=module.params["project_name"],
                operation=module.params["operation"] or "add",
                target_group=module.params["target_group"] or "",
                run_id=module.params["run_id"] or str(int(os.getpid())),
                force_recovery=module.params["force_recovery"],
            )
            module.exit_json(changed=True, lock_data=lock_data)

        elif action == "release_lock":
            released = lock.release(run_id=module.params["run_id"])
            module.exit_json(changed=released, released=released)

        elif action == "start_journal":
            j_data = journal.start(
                run_id=module.params["run_id"] or str(int(os.getpid())),
                project_name=module.params["project_name"],
                operation=module.params["operation"] or "add",
                target_group=module.params["target_group"] or "",
                planned_stages=module.params["planned_stages"],
            )
            module.exit_json(changed=True, journal=asdict(j_data))

        elif action == "record_stage":
            journal.record_stage(
                stage=module.params["stage"],
                status=module.params["stage_status"] or "verified",
            )
            module.exit_json(changed=True)

        elif action == "finish_journal":
            j_data = journal.finish(
                terminal_result=module.params["terminal_result"],
            )
            module.exit_json(changed=True, journal=asdict(j_data) if j_data else {})

        elif action == "plan_add":
            plan = LifecyclePlanner.plan_add(
                target_group=module.params["target_group"],
                effective_config={},
            )
            module.exit_json(changed=False, plan=plan)

        elif action == "plan_remove":
            plan = LifecyclePlanner.plan_remove(
                target_group=module.params["target_group"],
                mapped_nodes=module.params["mapped_nodes"],
                all_functional_groups=module.params["all_functional_groups"],
                ownership_evidence=module.params["ownership_evidence"] or None,
            )
            module.exit_json(changed=False, plan=plan)

        elif action == "plan_configure":
            plan = LifecyclePlanner.plan_configure(
                target_group=module.params["target_group"],
                configure_scope=module.params["configure_scope"],
            )
            module.exit_json(changed=False, plan=plan)

        elif action == "evaluate_recovery":
            j_data = journal.read()
            if not j_data:
                module.exit_json(changed=False, recovery_needed=False, remaining_stages=[])
            incomplete = BoundedRecoveryManager.evaluate_resumption(
                j_data, module.params["planned_stages"]
            )
            module.exit_json(
                changed=False,
                recovery_needed=len(incomplete) < len(module.params["planned_stages"]),
                remaining_stages=incomplete,
            )

    except (
        LockContentionError,
        NodeNotEmptiedError,
        OwnershipAmbiguityError,
        RecoveryRequiredError,
        LifecycleError,
    ) as exc:
        module.fail_json(msg=str(exc))
    except Exception as exc:  # pylint: disable=broad-exception-caught
        module.fail_json(msg=f"Unexpected lifecycle error: {exc}")


if __name__ == "__main__":
    main()
