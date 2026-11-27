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
# ****
# Secure code generated utilizing Code Guardian.
# Applicable rules used: CG-CONFIG-001.5, CG-DESER-001.1
# ****

"""OCI boot-ready contract verification (FR-1.5, TC-FVT-014, TC-FVT-015).

Fixtures are crafted from a real Thrillhouse base image in the local registry by
adding one layer with a whiteout, so no production tag is changed. Every fixture
is removed by manifest digest. Garbage collection is never run.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from omnia_auto import load_test_config

from ..vars.common_vars import (
    BOOT_BASE_REPO_MARKER,
    BOOT_CHECK_TIMEOUT,
    BOOT_FIXTURE_KINDS,
    BOOT_FIXTURE_NAMESPACE,
    BOOT_REGCTL_BIN,
    BOOT_REGISTRY_HOST,
    CMDS,
)

SRC_SUBPATH = "src/image_build_manager"
MODULES_SUBPATH = "plugins/modules"


def _image_build_src(host) -> str:
    """Return the Image Build Manager source path on the target host.

    Uses ``clone_path`` from the test config. When that path is absent and the
    suite runs on the repository host, falls back to the checkout that holds
    this test tree.

    Args:
        host: testinfra host object.

    Returns:
        The source path, or an empty string when none is usable.
    """
    clone_path = load_test_config().get("clone_path", "")
    candidates = [
        f"{clone_path}/{SRC_SUBPATH}",
        str(Path(__file__).resolve().parents[4] / SRC_SUBPATH),
    ]
    for src in candidates:
        if host.run(f"test -d {src}/{MODULES_SUBPATH}").rc == 0:
            return src
    return ""


def _regctl_config(host) -> str:
    """Create a temporary regctl config that allows the plain-HTTP local registry.

    Args:
        host: testinfra host object.

    Returns:
        The config path, or an empty string on failure.
    """
    path = host.run(CMDS["boot_cfg_path"]).stdout.strip()
    result = host.run(
        CMDS["boot_regctl_set_tls"].format(cfg=path, registry=BOOT_REGISTRY_HOST)
    )
    return path if path and result.rc == 0 else ""


def _find_base_image(host, cfg: str) -> Optional[Tuple[str, str]]:
    """Find a real Thrillhouse base image in the local registry.

    Args:
        host: testinfra host object.
        cfg: Temporary regctl config path.

    Returns:
        A (repository, tag) pair, or None when no base image is present.
    """
    del cfg
    catalog = host.run(CMDS["boot_catalog"].format(registry=BOOT_REGISTRY_HOST))
    try:
        repos = json.loads(catalog.stdout).get("repositories", [])
    except ValueError:
        return None
    for repo in repos:
        if BOOT_BASE_REPO_MARKER not in repo:
            continue
        tags_out = host.run(
            CMDS["boot_tags"].format(registry=BOOT_REGISTRY_HOST, repo=repo)
        )
        try:
            tags = json.loads(tags_out.stdout).get("tags") or []
        except ValueError:
            continue
        if tags:
            return repo, tags[0]
    return None


def _run_boot_ready(host, cfg: str, src: str, repo: str, tag: str) -> Dict[str, Any]:
    """Run the oci_boot_ready_check module against one image.

    Args:
        host: testinfra host object.
        cfg: Temporary regctl config path.
        src: Image Build Manager source path.
        repo: Repository without the registry host.
        tag: Image tag.

    Returns:
        Dict with ``success``, ``versions``, ``message`` and ``raw``.
    """
    full_repo = f"{BOOT_REGISTRY_HOST}/{repo}"
    result = host.run(
        CMDS["boot_ready_check"].format(
            src=src,
            cfg=cfg,
            repo=full_repo,
            ref=f"{full_repo}:{tag}",
            regctl=BOOT_REGCTL_BIN,
            timeout=BOOT_CHECK_TIMEOUT,
        )
    )
    out = result.stdout
    block = re.search(r'"complete_versions":\s*\[(.*?)\]', out, re.S)
    message = re.search(r'"msg":\s*"(.*?)"', out)
    return {
        "success": "SUCCESS" in out and "FAILED" not in out,
        "versions": re.findall(r'"([^"]+)"', block.group(1)) if block else [],
        "message": message.group(1) if message else "",
        "raw": out,
    }


def _layers(host, cfg: str, repo: str, tag: str) -> List[str]:
    """Return the layer digests of an image in manifest order.

    Args:
        host: testinfra host object.
        cfg: Temporary regctl config path.
        repo: Repository without the registry host.
        tag: Image tag.

    Returns:
        Layer digests, lowest layer first.
    """
    ref = f"{BOOT_REGISTRY_HOST}/{repo}:{tag}"
    out = host.run(CMDS["boot_layers"].format(cfg=cfg, ref=ref)).stdout
    return out.split()


def _build_fixture(host, cfg: str, base: Tuple[str, str], version: str, kind: str):
    """Create an incomplete image from the base image plus one whiteout layer.

    Args:
        host: testinfra host object.
        cfg: Temporary regctl config path.
        base: (repository, tag) of the real base image.
        version: Kernel version taken from the base image.
        kind: Key of ``BOOT_FIXTURE_KINDS``.

    Returns:
        A tuple of (repository, tag, stage_dir, tar_path, error).
    """
    directory, name, _ = BOOT_FIXTURE_KINDS[kind]
    stage = f"/tmp/fvt_boot_stage_{kind}"
    tar_path = f"/tmp/fvt_boot_layer_{kind}.tar"
    repo = f"{BOOT_FIXTURE_NAMESPACE}/{kind}"
    staged = host.run(
        CMDS["boot_stage_layer"].format(
            stage=stage,
            dir=directory.format(version=version),
            name=name.format(version=version),
            tar=tar_path,
        )
    )
    if staged.rc != 0:
        return repo, "1", stage, tar_path, "Failed to stage the fixture layer"
    created = host.run(
        CMDS["boot_image_mod_layer"].format(
            cfg=cfg,
            base=f"{BOOT_REGISTRY_HOST}/{base[0]}:{base[1]}",
            target=f"{BOOT_REGISTRY_HOST}/{repo}:1",
            tar=tar_path,
        )
    )
    error = "" if created.rc == 0 else created.stdout.strip()[:200]
    return repo, "1", stage, tar_path, error


def _delete_fixture(host, cfg: str, repo: str, tag: str) -> None:
    """Delete one fixture image by manifest digest. Never runs garbage collection.

    Args:
        host: testinfra host object.
        cfg: Temporary regctl config path.
        repo: Fixture repository without the registry host.
        tag: Fixture tag.
    """
    ref = f"{BOOT_REGISTRY_HOST}/{repo}:{tag}"
    digest = host.run(CMDS["boot_image_digest"].format(cfg=cfg, ref=ref))
    if digest.rc == 0 and digest.stdout.strip():
        host.run(
            CMDS["boot_manifest_delete"].format(
                cfg=cfg,
                repo=f"{BOOT_REGISTRY_HOST}/{repo}",
                digest=digest.stdout.strip(),
            )
        )


def _setup(host) -> Dict[str, Any]:
    """Resolve the source path, regctl config, and real base image.

    Args:
        host: testinfra host object.

    Returns:
        Dict with ``ok`` plus ``src``, ``cfg``, ``base`` or a ``details`` reason.
    """
    src = _image_build_src(host)
    if not src:
        return {"ok": False, "details": "Image Build Manager source not found"}
    cfg = _regctl_config(host)
    if not cfg:
        return {"ok": False, "details": "Could not create a regctl config"}
    base = _find_base_image(host, cfg)
    if base is None:
        return {"ok": False, "details": "No Thrillhouse base image in the registry"}
    return {"ok": True, "src": src, "cfg": cfg, "base": base}


def check_boot_ready_complete(host) -> Dict[str, Any]:
    """Verify a real Thrillhouse image is accepted by the boot-ready check.

    Args:
        host: testinfra host object.

    Returns:
        Dict with ``success``, ``versions``, ``details`` and ``error``.
    """
    setup = _setup(host)
    if not setup["ok"]:
        return {"success": True, "skipped": True, "details": setup["details"]}
    try:
        result = _run_boot_ready(host, setup["cfg"], setup["src"], *setup["base"])
    finally:
        host.run(CMDS["boot_cleanup_files"].format(stage="", tar="", cfg=setup["cfg"]))
    return {
        "success": result["success"] and bool(result["versions"]),
        "versions": result["versions"],
        "details": ", ".join(result["versions"]),
        "error": result["message"] or "no complete boot set reported",
    }


def check_boot_ready_incomplete(host, kind: str) -> Dict[str, Any]:  # pylint: disable=too-many-locals
    """Verify an incomplete image is rejected and the missing path is named.

    Args:
        host: testinfra host object.
        kind: Key of ``BOOT_FIXTURE_KINDS``.

    Returns:
        Dict with ``success``, ``expected_path``, ``details`` and ``error``.
    """
    setup = _setup(host)
    if not setup["ok"]:
        return {"success": True, "skipped": True, "details": setup["details"]}
    cfg, src, base = setup["cfg"], setup["src"], setup["base"]
    base_result = _run_boot_ready(host, cfg, src, *base)
    if not base_result["versions"]:
        return {"success": False, "error": "base image is not boot-ready"}
    version = base_result["versions"][0]
    expected = BOOT_FIXTURE_KINDS[kind][2].format(version=version)
    repo, tag, stage, tar_path, error = _build_fixture(host, cfg, base, version, kind)
    try:
        if error:
            return {"success": False, "expected_path": expected, "error": error}
        result = _run_boot_ready(host, cfg, src, repo, tag)
        rejected = (not result["success"]) and expected in result["message"]
        return {
            "success": rejected,
            "expected_path": expected,
            "details": result["message"],
            "error": result["message"] or "image was accepted",
        }
    finally:
        _delete_fixture(host, cfg, repo, tag)
        host.run(CMDS["boot_cleanup_files"].format(stage=stage, tar=tar_path, cfg=cfg))


def check_layers_preserved(host) -> Dict[str, Any]:  # pylint: disable=too-many-locals
    """Verify layers are preserved and each base layer is stored once.

    A derived image must keep every base layer, in order, and add exactly one
    layer. Each base layer blob must exist once in the registry storage.

    Args:
        host: testinfra host object.

    Returns:
        Dict with ``success``, ``shared`` (count) and ``error``.
    """
    setup = _setup(host)
    if not setup["ok"]:
        return {"success": True, "skipped": True, "details": setup["details"]}
    cfg, src, base = setup["cfg"], setup["src"], setup["base"]
    base_result = _run_boot_ready(host, cfg, src, *base)
    if not base_result["versions"]:
        return {"success": False, "error": "base image is not boot-ready"}
    kind = "no_initramfs"
    repo, tag, stage, tar_path, error = _build_fixture(
        host, cfg, base, base_result["versions"][0], kind
    )
    try:
        if error:
            return {"success": False, "error": error}
        base_layers = _layers(host, cfg, *base)
        new_layers = _layers(host, cfg, repo, tag)
        preserved = new_layers[: len(base_layers)] == base_layers
        added_one = len(new_layers) == len(base_layers) + 1
        data = host.run(CMDS["boot_registry_data_dir"].format()).stdout.strip()
        stored_once = all(
            host.run(
                CMDS["boot_count_blob_dirs"].format(
                    data=data, hex=digest.split(":", 1)[-1]
                )
            ).stdout.strip()
            == "1"
            for digest in base_layers
        )
        return {
            "success": preserved and added_one and stored_once,
            "shared": len(base_layers),
            "error": (
                f"preserved={preserved} added_one={added_one} "
                f"stored_once={stored_once}"
            ),
        }
    finally:
        _delete_fixture(host, cfg, repo, tag)
        host.run(CMDS["boot_cleanup_files"].format(stage=stage, tar=tar_path, cfg=cfg))
