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

"""Run omnia.sh and domain playbooks on the OIM with live output.

``omnia_auto.run_playbook`` has no ``--skip-tags`` support, which the
build_stream and image_build_manager cleanups need to preserve credentials,
so playbooks are launched through the same streaming/SSH helpers it uses.
"""

import os
import shlex
from typing import Any, Dict, List, Optional

from omnia_auto import is_local_execution, load_test_config, load_test_credentials
from omnia_auto.functions.process_security import descriptor_tuple, sshpass_pipe
from omnia_auto.functions.runner_func import _fail, _stream_cmd, _wrap_ssh

from .config_func import to_ansible_extra_vars
from .probe_func import render_cmd
from ..vars.common_vars import NO_TIMEOUT, OMNIA_ENV_FILE, OMNIA_SH_WORKDIR, REPO_ROOT


def _repository_root(config: Dict[str, Any]) -> str:
    """Return the omnia checkout used on the execution host."""
    if is_local_execution():
        return REPO_ROOT
    clone_path = config.get("clone_path", "")
    if not clone_path:
        raise ValueError(
            "'clone_path' must be set in test_config.yml for remote execution"
        )
    return clone_path


def repository_path(relative: str) -> str:
    """Return ``relative`` resolved inside the omnia checkout on the OIM."""
    return os.path.join(_repository_root(load_test_config()), relative)


def run_streamed(command: str, label: str, workdir: str,
                 timeout: float = NO_TIMEOUT) -> Dict[str, Any]:
    """Run a shell command on the OIM and stream its output live.

    Local mode runs the command directly; remote mode wraps it in SSH using
    the same connection settings as ``omnia_auto.run_playbook``. The command
    runs until it finishes (no timeout) unless ``timeout`` is given.

    Returns:
        Dict with keys: success, rc, output, duration, error, command.
    """
    config = load_test_config()
    if is_local_execution():
        result = _stream_cmd(command, label, timeout, None, config, workdir)
        return {**result, "command": command}
    credentials = load_test_credentials()
    try:
        with sshpass_pipe(credentials.get("oim_password", "")) as auth_fd:
            ssh_cmd = _wrap_ssh(command, config, credentials, auth_fd=auth_fd)
            result = _stream_cmd(
                ssh_cmd, label, timeout, None, config, workdir,
                pass_fds=descriptor_tuple(auth_fd),
            )
    except (OSError, ValueError) as exc:
        result = _fail(label, 0.0, str(exc))
    return {**result, "command": command}


def run_omnia_sh(arguments: str) -> Dict[str, Any]:
    """Run ``./omnia.sh <arguments>`` from ``src/main`` until it finishes.

    Returns:
        Dict with keys: success, rc, output, duration, error, command.
    """
    label = f"./omnia.sh {arguments}"
    try:
        workdir = repository_path(OMNIA_SH_WORKDIR)
    except (OSError, RuntimeError, ValueError) as exc:
        return {**_fail(label, 0.0, str(exc)), "command": label}
    if is_local_execution() and not os.path.isfile(os.path.join(workdir, "omnia.sh")):
        return {**_fail(label, 0.0, f"omnia.sh not found in {workdir}"), "command": label}
    arg_string = " ".join(shlex.quote(part) for part in shlex.split(arguments))
    command = render_cmd("omnia_sh", workdir=workdir, arguments=arg_string)
    return run_streamed(command, label, OMNIA_SH_WORKDIR)


def playbook_arguments(tag: Optional[str], extra_vars: Dict[str, Any],
                       skip_tags: Optional[List[str]] = None) -> List[str]:
    """Return the ansible-playbook arguments (unquoted) for a run."""
    arguments = [f"--tags={tag}"] if tag else []
    if skip_tags:
        arguments.append(f"--skip-tags={','.join(skip_tags)}")
    for key, value in to_ansible_extra_vars(extra_vars).items():
        arguments.extend(["-e", f"{key}={value}"])
    return arguments


def run_ansible_playbook(playbook: str, workdir: str,
                         tag: Optional[str] = None,
                         extra_vars: Optional[Dict[str, Any]] = None,
                         skip_tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """Run a domain playbook from the omnia checkout until it finishes.

    omnia.env is sourced and OMNIA_VENV_PATH activated exactly as
    ``omnia_auto.run_playbook`` does. Output is streamed live.

    Returns:
        Dict with keys: success, rc, output, duration, error, command.
    """
    arguments = playbook_arguments(tag, extra_vars or {}, skip_tags)
    label = " ".join(["ansible-playbook", playbook, *arguments])
    try:
        absolute_workdir = repository_path(workdir)
    except (OSError, RuntimeError, ValueError) as exc:
        return {**_fail(playbook, 0.0, str(exc)), "command": label}
    command = render_cmd(
        "ansible_playbook",
        env_file=OMNIA_ENV_FILE,
        workdir=absolute_workdir,
        playbook=playbook,
        arguments=" ".join(shlex.quote(part) for part in arguments),
    )
    result = run_streamed(command, playbook, workdir)
    return {**result, "command": label}


def run_domain_cleanup(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Run one domain cleanup playbook from a ``cleanup_plan`` entry."""
    spec = entry["spec"]
    return run_ansible_playbook(
        spec["playbook"], spec["workdir"],
        tag=spec["tag"], extra_vars=entry["extra_vars"], skip_tags=entry["skip_tags"],
    )


def cleanup_command(entry: Dict[str, Any]) -> str:
    """Return a readable ansible-playbook command for a cleanup entry."""
    spec = entry["spec"]
    return " ".join([
        "ansible-playbook", spec["playbook"],
        *playbook_arguments(spec["tag"], entry["extra_vars"], entry["skip_tags"]),
    ])
