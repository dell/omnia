# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Resolve Git refs and create immutable source archives safely."""

import os
import re
import subprocess
import tempfile


_OBJECT_ID = re.compile(r"^[0-9a-fA-F]{40,64}$")


def _run_git(command, timeout=600):
    """Run one structured Git command and return standard output."""
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.stdout


def resolve_git_ref(url, version):
    """Resolve an exact remote tag or branch to an immutable object ID.

    Annotated tags resolve to their peeled commit. A missing or ambiguous
    ref fails closed instead of silently cloning the remote default branch.
    """
    version = str(version or "")
    if (
            not version
            or version.startswith("-")
            or any(character.isspace() for character in version)
            or any(ord(character) < 32 for character in version)):
        raise ValueError("Git version is not a safe branch or tag name")

    tag_ref = f"refs/tags/{version}"
    peeled_tag_ref = f"{tag_ref}^{{}}"
    branch_ref = f"refs/heads/{version}"
    output = _run_git([
        "git", "ls-remote", url, tag_ref, peeled_tag_ref, branch_ref,
    ], timeout=300)
    resolved = {}
    for line in output.splitlines():
        parts = line.split("\t", maxsplit=1)
        if len(parts) != 2 or not _OBJECT_ID.fullmatch(parts[0]):
            raise ValueError("Git remote returned an invalid object ID")
        if parts[1] in (tag_ref, peeled_tag_ref, branch_ref):
            resolved[parts[1]] = parts[0].lower()

    tag_object = resolved.get(peeled_tag_ref) or resolved.get(tag_ref)
    branch_object = resolved.get(branch_ref)
    if tag_object and branch_object and tag_object != branch_object:
        raise ValueError("Git version matches different tag and branch objects")
    object_id = tag_object or branch_object
    if not object_id:
        raise ValueError("Git branch or tag was not found")
    return object_id


def create_git_tarball(url, version, object_id, package_name, destination):
    """Clone the selected ref and atomically create a deterministic archive."""
    destination_directory = os.path.dirname(destination)
    os.makedirs(destination_directory, exist_ok=True)
    with tempfile.TemporaryDirectory(
            prefix=".git-source-", dir=destination_directory) as work_directory:
        clone_directory = os.path.join(work_directory, "repository")
        _run_git([
            "git", "clone", "--quiet", "--no-checkout", "--filter=blob:none",
            "--branch", version, "--single-branch", "--", url,
            clone_directory,
        ])
        resolved_head = _run_git([
            "git", "-C", clone_directory, "rev-parse", "HEAD^{commit}",
        ]).strip().lower()
        if resolved_head != object_id:
            raise ValueError("Git ref changed while the source was downloaded")

        temporary_archive = os.path.join(work_directory, "archive.tar.gz")
        _run_git([
            "git", "-C", clone_directory, "archive", "--format=tar.gz",
            f"--prefix={package_name}/", f"--output={temporary_archive}",
            object_id,
        ])
        if not os.path.isfile(temporary_archive):
            raise OSError("Git archive was not created")
        os.replace(temporary_archive, destination)
    return destination
