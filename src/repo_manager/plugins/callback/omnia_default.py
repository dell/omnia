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

"""
Custom Ansible stdout callback plugin for Omnia.

Extends the built-in ``default`` callback to suppress the ``[ERROR]``
source-context block introduced in ansible-core 2.19/2.20 (Data Tagging).
Renders multiline ``msg`` fields with real newlines on failure.
All other output (task banners, ok/changed/skipped lines, play recaps,
etc.) is unchanged.

Usage — add to every ``ansible.cfg``::

    [defaults]
    stdout_callback = omnia_default
    callback_plugins = <relative-path-to>/common/callback_plugins
"""
from __future__ import annotations

import json
import os
import re
import stat

from ansible import constants as C  # pylint: disable=no-name-in-module
from ansible.errors import AnsibleError
from ansible.plugins.callback.default import CallbackModule as DefaultCallback

DOCUMENTATION = r"""
    name: omnia_default
    type: stdout
    short_description: Omnia default stdout callback
    version_added: "2.1"
    description:
        - Inherits every behaviour of the built-in C(default) callback.
        - Suppresses the C([ERROR]) source-context block added in
          ansible-core 2.19/2.20.
        - Renders multiline C(msg) fields with real newlines on failure.
        - Produces only the classic single-line C(fatal:) output.
    extends_documentation_fragment:
        - default_callback
"""

# Pattern to detect the 2.19/2.20 [ERROR] task-failure context block
_ERROR_CONTEXT_PATTERN = re.compile(
    r"\[ERROR\]:\s*Task failed:|"
    r"\[ERROR\]:\s*Action failed:|"
    r"Origin:\s+\S+\.ya?ml:\d+:\d+|"
    r"\s+\^\s+column\s+\d+"
)

_LOG_DIRECTORY_MODE = 0o700
_LOG_FILE_MODE = 0o600


def _secure_log_file(log_filepath):
    """Create or restrict the controller log without module-utils imports."""
    log_dir = os.path.dirname(log_filepath) or "."
    os.makedirs(log_dir, mode=_LOG_DIRECTORY_MODE, exist_ok=True)

    directory_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        directory_flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        directory_flags |= os.O_NOFOLLOW
    directory_descriptor = os.open(log_dir, directory_flags)
    try:
        if not stat.S_ISDIR(os.fstat(directory_descriptor).st_mode):
            raise OSError("Ansible log directory path is not a directory")
        os.fchmod(directory_descriptor, _LOG_DIRECTORY_MODE)

        file_flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NONBLOCK
        if hasattr(os, "O_NOFOLLOW"):
            file_flags |= os.O_NOFOLLOW
        file_descriptor = os.open(
            os.path.basename(log_filepath),
            file_flags,
            _LOG_FILE_MODE,
            dir_fd=directory_descriptor,
        )
        try:
            if not stat.S_ISREG(os.fstat(file_descriptor).st_mode):
                raise OSError("Ansible log path is not a regular file")
            os.fchmod(file_descriptor, _LOG_FILE_MODE)
        finally:
            os.close(file_descriptor)
    finally:
        os.close(directory_descriptor)


class CallbackModule(DefaultCallback):  # pylint: disable=too-many-ancestors
    """
    Omnia stdout callback plugin.

    Extends the built-in default callback to suppress the ``[ERROR]``
    source-context block introduced in ansible-core 2.19/2.20 and
    renders multiline failure messages with real newlines.
    """

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = "stdout"
    CALLBACK_NAME = "omnia_default"

    def __init__(self):
        super().__init__()
        self._secure_ansible_log()
        self._patched = False

    @staticmethod
    def _secure_ansible_log():
        """Restrict the configured Ansible log before task output is written."""
        log_path = getattr(C, "DEFAULT_LOG_PATH", "")
        if not log_path:
            return
        try:
            _secure_log_file(os.path.abspath(log_path))
        except OSError as error:
            raise AnsibleError(
                "Unable to create the Ansible log with restricted permissions."
            ) from error

    def _patch_display(self):
        """Monkey-patch Display.display to drop [ERROR] context blocks."""
        if self._patched:
            return
        self._patched = True

        original_display = self._display.display

        def filtered_display(msg, *args, **kwargs):
            msg_str = str(msg)
            if _ERROR_CONTEXT_PATTERN.search(msg_str):
                return
            original_display(msg, *args, **kwargs)

        self._display.display = filtered_display

    def set_options(self, task_keys=None, var_options=None, direct=None):
        """Load options and apply the display patch."""
        super().set_options(task_keys=task_keys, var_options=var_options, direct=direct)
        self._patch_display()

    def v2_playbook_on_play_start(self, play):
        """Ensure patch is active before the first play."""
        self._patch_display()
        super().v2_playbook_on_play_start(play)

    def _format_result_msg(self, result_dict):
        """
        Format result dict for display.

        If ``msg`` contains newlines, display them as real line breaks
        instead of escaped ``\\n`` characters.
        """
        msg = result_dict.get("msg", "")
        if isinstance(msg, str) and "\n" in msg:
            filtered = {k: v for k, v in result_dict.items() if k != "msg"}
            return f"{json.dumps(filtered, sort_keys=True)}\nmsg: |-\n  {msg.replace(chr(10), chr(10) + '  ')}"
        return self._dump_results(result_dict)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        """
        Render task failures as the classic single-line ``fatal:`` message.

        The ``[ERROR]`` block is suppressed by the ``Display.display`` patch.
        Multiline ``msg`` values are rendered with real newlines.
        """
        # pylint: disable=protected-access
        self._patch_display()
        delegated_vars = result._result.get("_ansible_delegated_vars", None)
        self._clean_results(result._result, result._task.action)

        if self._last_task_banner != result._task._uuid:
            self._print_task_banner(result._task)

        self._handle_exception(
            result._result,
            use_stderr=self.get_option("display_failed_stderr"),
        )
        self._handle_warnings(result._result)

        if result._task.loop and "results" in result._result:
            self._process_items(result)
        else:
            formatted = self._format_result_msg(result._result)
            host_name = result._host.get_name()
            stderr_opt = self.get_option("display_failed_stderr")
            color = getattr(C, "COLOR_ERROR", "red")

            if delegated_vars:
                self._display.display(
                    f"fatal: [{host_name} -> {delegated_vars['ansible_host']}]: FAILED! => {formatted}",
                    color=color,
                    stderr=stderr_opt,
                )
            else:
                self._display.display(
                    f"fatal: [{host_name}]: FAILED! => {formatted}",
                    color=color,
                    stderr=stderr_opt,
                )

        if ignore_errors:
            color_skip = getattr(C, "COLOR_SKIP", "cyan")
            self._display.display("...ignoring", color=color_skip)
        # pylint: enable=protected-access

    def v2_playbook_on_stats(self, stats):
        """Ensure patch is active during PLAY RECAP to suppress replayed errors."""
        self._patch_display()
        super().v2_playbook_on_stats(stats)

    def _display_error_context(self, *args, **kwargs):
        """Intentionally suppressed — prevents [ERROR] source-context rendering."""
