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

"""Scenario prechecks: the first exec test of every scenario.

Each precheck proves, without changing the system, that the scenario's
entry point can run unattended. A failed precheck skips the rest of the
scenario (conftest), so a multi-hour entry point never starts on a host
that cannot finish it. Every function returns a verifier result
(``summarize``): name, success, fields, failures.
"""

import posixpath
from typing import Any, Dict, List, Sequence

from .catalog_func import catalog_target, read_catalog, resolve_catalog_source
from .command_func import repository_path, run_ansible_playbook
from .probe_func import (
    Probe,
    container_running,
    credential_store_probes,
    domain_input_path,
    env_var_set,
    file_present,
    run_cmd,
    summarize,
    unit_active,
)
from .auto_cleanup_func import retention_settings
from ..vars.common_vars import (
    BSM_CONFIG_FILE,
    BSM_CONTAINER,
    BSM_DOMAIN,
    BSM_PLAYBOOK,
    BSM_PLAYBOOK_WATCHER_SERVICE,
    BSM_PLAYBOOK_WORKDIR,
    BSM_PRECHECK_TAG,
    ENV_OMNIA_VENV_PATH,
    OMNIA_SH_FILE,
    OMNIA_SH_WORKDIR,
    PREPARE_BASE_DOMAINS,
    PXE_MAPPING_FILE,
    PXE_MAPPING_MIN_NODES,
    REQUIRED_ENV_VARS,
    VENV_ACTIVATE_FILE,
)


def _environment_probes(host: Any) -> List[Probe]:
    """omnia.env variables, the shared venv and the omnia.sh entry point."""
    probes = [env_var_set(host, name) for name in REQUIRED_ENV_VARS]
    _, venv, venv_set = probes[REQUIRED_ENV_VARS.index(ENV_OMNIA_VENV_PATH)]
    if venv_set:
        probes.append(file_present(host, posixpath.join(venv, VENV_ACTIVATE_FILE)))
    probes.append(file_present(
        host, posixpath.join(repository_path(OMNIA_SH_WORKDIR), OMNIA_SH_FILE)))
    return probes


def _credential_probes(host: Any, domains: Sequence[str]) -> List[Probe]:
    """Credential stores of ``domains`` (no store means an interactive prompt)."""
    probes: List[Probe] = []
    for domain in domains:
        try:
            probes.extend(credential_store_probes(host, domain))
        except ValueError as exc:
            probes.append((f"{domain} credentials", str(exc), False))
    return probes


def precheck_prepare_base(host: Any, catalog_selection: str = "") -> Dict[str, Any]:
    """Check that ``./omnia.sh --prepare-base`` can run unattended.

    Verifies the omnia.env variables, the shared venv, omnia.sh in the
    checkout and the repo_manager, image_build_manager and orchestrator
    credential stores. omnia.sh validates the domain inputs itself.

    When *catalog_selection* is a non-empty catalog number or path (from
    ``installation.catalog`` in test_config.yml), the selected catalog is
    resolved and placed at CATALOG_FILE_PATH so that it is available before
    prepare_base runs.

    Returns:
        Dict with keys: name, success, fields, failures.
    """
    probes = _environment_probes(host) + _credential_probes(host, PREPARE_BASE_DOMAINS)

    if catalog_selection:
        from .catalog_func import catalog_target, place_catalog
        target = catalog_target(host)
        if target["success"]:
            result = place_catalog(host, catalog_selection)
            if result["success"]:
                label = (f"Catalog placed at {result['target']}"
                         f" ({result['identifier']} v{result['version']})")
                probes.append(("Catalog placement", label, True))
            else:
                probes.append(("Catalog placement", result["error"], False))
        else:
            probes.append(("Catalog placement",
                           f"CATALOG_FILE_PATH not configured: {target['error']}", False))

    return summarize("precheck_prepare_base", probes)


def pxe_node_rows(host: Any) -> Probe:
    """Check that the PXE mapping holds enough node rows for the deploy test."""
    try:
        path = f"{domain_input_path(host, 'orchestrator')}/{PXE_MAPPING_FILE}"
    except ValueError as exc:
        return PXE_MAPPING_FILE, str(exc), False
    result = run_cmd(host, "cat_file", path=path)
    if result.rc != 0:
        return f"Node rows in {path}", "MISSING", False
    rows = [line for line in result.stdout.splitlines()[1:] if line.strip()]
    ok = len(rows) >= PXE_MAPPING_MIN_NODES
    return (f"Node rows in {path}",
            str(len(rows)) if ok else f"{len(rows)} (need {PXE_MAPPING_MIN_NODES})", ok)


def _catalog_probes(host: Any, selection: str) -> List[Probe]:
    """The selected catalog resolves to a valid catalog and the target is valid."""
    target = catalog_target(host)
    probes = [("CATALOG_FILE_PATH", target["path"] if target["success"] else target["error"],
               target["success"])]
    source = resolve_catalog_source(host, selection)
    if not source["success"]:
        return probes + [(f"Catalog {selection}", source["error"], False)]
    parsed = read_catalog(host, source["path"])
    probes.append((f"Catalog {selection}",
                   f"{source['path']} ({parsed['identifier']} v{parsed['version']})"
                   if parsed["success"] else parsed["error"], parsed["success"]))
    return probes


def precheck_installation(host: Any, settings: Dict[str, Any]) -> Dict[str, Any]:
    """Check that build_stream.yml can install BuildStream unattended.

    Verifies the selected catalog and CATALOG_FILE_PATH, the BuildStream
    configuration and credential store, enough PXE node rows for the deploy
    pipeline, and runs ``build_stream.yml --tags precheck`` (the product
    check that repo_manager and image_build_manager are ready).

    Returns:
        Dict with keys: name, success, fields, failures.
    """
    probes = _catalog_probes(host, settings["catalog"])
    probes.extend(_credential_probes(host, (BSM_DOMAIN,)))
    try:
        probes.append(file_present(host, f"{domain_input_path(host, BSM_DOMAIN)}/"
                                         f"{BSM_CONFIG_FILE}"))
    except ValueError as exc:
        probes.append((BSM_CONFIG_FILE, str(exc), False))
    probes.append(pxe_node_rows(host))
    run = run_ansible_playbook(BSM_PLAYBOOK, BSM_PLAYBOOK_WORKDIR, tag=BSM_PRECHECK_TAG)
    probes.append((run["command"], f"rc={run['rc']}", run["success"]))
    return summarize("precheck_installation", probes)


def precheck_auto_cleanup(host: Any) -> Dict[str, Any]:
    """Check that one automated cleanup pass can run and be finalized.

    Verifies the ``retention`` settings (as the scheduler validates them),
    the omnia_build_stream container (runs the pass) and playbook-watcher
    (runs the cleanup playbook that finalizes CLEANING groups).

    Returns:
        Dict with keys: name, success, fields, failures, config (effective
        retention settings), path (build_stream_config.yml), enabled.
    """
    settings = retention_settings(host)
    probes = [(f"retention in {settings['path']}",
               "valid" if settings["success"] else settings["error"], settings["success"]),
              container_running(host, BSM_CONTAINER),
              unit_active(host, BSM_PLAYBOOK_WATCHER_SERVICE)]
    result = summarize("precheck_auto_cleanup", probes)
    result.update(config=settings["config"], path=settings["path"],
                  enabled=bool(settings["config"].get("auto_cleanup_enabled")))
    return result


def precheck_cleanup(host: Any, plan: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Check that every enabled domain cleanup can run.

    Verifies that at least one domain is enabled, that each enabled domain's
    playbook exists in the checkout, and the omnia.env variables the cleanup
    verification resolves paths from.

    Returns:
        Dict with keys: name, success, fields, failures.
    """
    enabled = [entry for entry in plan if entry["enabled"]]
    probes: List[Probe] = [("Enabled domains",
                            ", ".join(entry["name"] for entry in enabled) or "NONE",
                            bool(enabled))]
    probes.extend(env_var_set(host, name) for name in REQUIRED_ENV_VARS)
    for entry in enabled:
        spec = entry["spec"]
        probes.append(file_present(
            host, posixpath.join(repository_path(spec["workdir"]), spec["playbook"])))
    return summarize("precheck_cleanup", probes)
