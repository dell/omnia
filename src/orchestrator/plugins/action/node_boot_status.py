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

"""Keep transient SSH failures retryable for node boot verification."""

from __future__ import annotations

from ansible.errors import (
    AnsibleAuthenticationFailure,
    AnsibleConnectionFailure,
    AnsibleError,
)
from ansible.module_utils.common.text.converters import to_text
from ansible.plugins.action import ActionBase


class ActionModule(ActionBase):
    """Execute the node-local module and normalize connection failures."""

    # _execute_module creates the remote temporary path inside the guarded
    # block, allowing transient connection failures to become retryable data.
    TRANSFERS_FILES = False
    _VALID_ARGS = frozenset(("pxe_start_epoch",))

    def run(self, tmp=None, task_vars=None):
        """Return a retryable result when the node is temporarily unreachable."""
        if task_vars is None:
            task_vars = {}

        result = super().run(tmp, task_vars)
        del tmp
        try:
            # _execute_module injects private _ansible_* transport fields into
            # its argument mapping.  Do not pass the task's reusable mapping
            # directly: an ``until`` retry would feed those injected fields
            # back to AnsibleModule as unsupported user options.
            module_args = {
                key: value
                for key, value in self._task.args.items()
                if key in self._VALID_ARGS
            }
            result.update(
                self._execute_module(
                    module_args=module_args,
                    task_vars=task_vars,
                )
            )
        except AnsibleError as error:
            connection_error = isinstance(
                error, (AnsibleAuthenticationFailure, AnsibleConnectionFailure)
            ) or isinstance(
                error.__cause__,
                (AnsibleAuthenticationFailure, AnsibleConnectionFailure),
            )
            inventory_hostname = task_vars.get("inventory_hostname", "target node")
            if connection_error:
                try:
                    self._connection.reset()
                except (AttributeError, AnsibleError):
                    pass
                error_text = to_text(error, errors="surrogate_or_replace")[:500]
                detail = (
                    f"Passwordless root SSH failed on {inventory_hostname}: "
                    f"{error_text}"
                )
            else:
                error_text = to_text(error, errors="surrogate_or_replace")[:500]
                detail = (
                    f"Node boot verification could not run on {inventory_hostname}: "
                    f"{error_text}"
                )
            result.update(
                {
                    "changed": False,
                    "terminal": not connection_error,
                    "state": "unreachable" if connection_error else "verification_error",
                    "detail": detail,
                    "boot": {},
                    "cloud_init": {},
                }
            )
        return result
