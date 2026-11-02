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

"""Domain install: ``./omnia.sh --setup-venv`` precheck and verification.

``--setup-venv`` creates or updates the shared venv, then runs every domain's
``domain-init.sh``, which installs dependencies, creates log directories and
copies the domain input files to ``<OMNIA_DATA_PATH>/<domain>/input/<project>``.
No domain cleanup removes the setup; only the disabled-by-default ``main``
cleanup block (``./omnia.sh --cleanup``) does.
"""

import posixpath
from typing import Any, Dict, List

from omnia_auto import read_remote_env

from .command_func import repository_path
from .probe_func import (
    Probe,
    domain_data_path,
    env_var_set,
    file_present,
    run_cmd,
    summarize_probes,
)
from ..vars.common_vars import (
    DOMAIN_INIT_ANSIBLE_LOG_DIR,
    DOMAIN_INIT_APP_SOURCE,
    DOMAIN_INIT_PROJECT_DIRS,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    ENV_OMNIA_VENV_PATH,
    INIT_DOMAINS,
    MAIN_ACTIVATE_SCRIPT,
    MAIN_SETUP_FILES,
    OMNIA_SH_FILE,
    OMNIA_SH_WORKDIR,
    PREPARE_BASE_REQUIRED_ENV_VARS,
    VENV_ACTIVATE_FILE,
)


def precheck_domain_install(host: Any) -> Dict[str, Any]:
    """Check that ``./omnia.sh --setup-venv`` can start (changes nothing).

    omnia.sh and every domain initializer must exist in the checkout. omnia.env
    is not required: the setup creates /etc/omnia/omnia.env.

    Returns:
        Dict with keys: name, success, fields, failures.
    """
    probes: List[Probe] = [file_present(
        host, posixpath.join(repository_path(OMNIA_SH_WORKDIR), OMNIA_SH_FILE))]
    probes.extend(file_present(host, posixpath.join(
        repository_path(f"src/{domain}"), "domain-init.sh")) for domain in INIT_DOMAINS)
    return summarize_probes("precheck_domain_install", probes)


def _directory_probe(host: Any, path: str) -> Probe:
    """A directory exists on the OIM."""
    present = run_cmd(host, "dir_exists", path=path).rc == 0
    return f"Directory {path}", "present" if present else "MISSING", present


def _input_file_probes(host: Any, domain: str, input_dir: str) -> List[Probe]:
    """One probe per file of ``src/<domain>/input``: staged in ``input_dir`` or not."""
    source_dir = repository_path(f"src/{domain}/input")
    expected = sorted(run_cmd(host, "list_input_files", path=source_dir).stdout.split())
    if not expected:
        return [(f"Source input files in {source_dir}", "NONE FOUND", False)]
    staged = set(run_cmd(host, "list_input_files", path=input_dir).stdout.split())
    return [(f"Input {posixpath.join(input_dir, name)}",
             "staged" if name in staged else "MISSING", name in staged) for name in expected]


def _app_source_probe(host: Any, domain: str, data_dir: str) -> List[Probe]:
    """The deployed application copy matches the checkout (build_stream only)."""
    relative = DOMAIN_INIT_APP_SOURCE.get(domain)
    if not relative:
        return []
    drift = run_cmd(host, "app_source_drift", src=repository_path(relative),
                    dest=data_dir).stdout.split()
    if not drift:
        return [(f"Application copy in {data_dir}", f"matches {relative}", True)]
    sample = ", ".join(path.removeprefix("./") for path in drift[:5])
    more = f" (+{len(drift) - 5} more)" if len(drift) > 5 else ""
    return [(f"Application copy in {data_dir}",
             f"{len(drift)} file(s) DIFFER from {relative}: {sample}{more}", False)]


def verify_main_setup(host: Any) -> Dict[str, Any]:
    """Verify the shared setup: omnia.env values, the venv and the activation script.

    Returns:
        Dict with keys: name, success, fields, failures.
    """
    probes: List[Probe] = [file_present(host, path) for path in MAIN_SETUP_FILES]
    probes.extend(env_var_set(host, name) for name in PREPARE_BASE_REQUIRED_ENV_VARS)
    for name, relative in ((ENV_OMNIA_VENV_PATH, VENV_ACTIVATE_FILE),
                           (ENV_OMNIA_DATA_PATH, MAIN_ACTIVATE_SCRIPT)):
        try:
            base = read_remote_env(host, name)
        except ValueError:
            probes.append((f"omnia.env {name}", "NOT SET", False))
            continue
        probes.append(file_present(host, posixpath.join(base, relative)))
    return summarize_probes("main_setup", probes)


def verify_domain_initialized(host: Any, domain: str) -> Dict[str, Any]:
    """Verify what ``domain-init.sh`` of ``domain`` creates.

    Every source input file is staged under ``<data>/input/<project>``, the
    project input/output/log directories and ``/var/log/omnia/<domain>``
    exist, and (build_stream) the application copy matches the checkout.

    Returns:
        Dict with keys: name, success, fields, failures.
    """
    try:
        data_dir = domain_data_path(host, domain)
        project = read_remote_env(host, ENV_OMNIA_PROJECT_NAME)
    except ValueError as exc:
        return summarize_probes(f"{domain}_initialized",
                                [(f"{domain} data path", str(exc), False)])
    probes: List[Probe] = [_directory_probe(host, posixpath.join(data_dir, kind, project))
                           for kind in DOMAIN_INIT_PROJECT_DIRS]
    probes.append(_directory_probe(host, DOMAIN_INIT_ANSIBLE_LOG_DIR.format(domain=domain)))
    probes.extend(_input_file_probes(host, domain, posixpath.join(data_dir, "input", project)))
    probes.extend(_app_source_probe(host, domain, data_dir))
    return summarize_probes(f"{domain}_initialized", probes)
