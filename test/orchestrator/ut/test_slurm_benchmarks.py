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

"""Execute real downloader logic and verify FVT mount and cleanup behavior."""

# pylint: disable=protected-access,redefined-outer-name

import io
import os
import re
import shlex
import subprocess
import tarfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import jinja2
import pytest
from library.functions import slurm_benchmark_pxeboot_func as benchmark
from library.vars.slurm_benchmark_vars import (
    BENCHMARK_COMMANDS,
    BENCHMARK_SNAPSHOT_SCRIPT,
    BENCHMARK_TOOLS,
)

REPO = Path(__file__).resolve().parents[3]
TEMPLATES = REPO / "src/orchestrator/roles/slurm_config/templates"


@pytest.fixture
def downloader(tmp_path):
    """Render the production script with a local fake Pulp transport."""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    template = jinja2.Template((TEMPLATES / "pull_benchmarks.sh.j2").read_text())
    script = scripts / "pull_benchmarks.sh"
    script.write_text(
        template.render(hostvars={"localhost": {"admin_nic_ip": "mirror"}})
    )
    script.chmod(0o755)
    (scripts / "omnia_platform.sh").write_text("""omnia_detect_platform() {
OMNIA_OS_TYPE=rhel
OMNIA_OS_VERSION=10.0
OMNIA_ARCH="${TEST_ARCH:-x86_64}"
OMNIA_PLATFORM_ROOT="$OMNIA_HPC_TOOLS_DIR/platforms/rhel/10.0/$OMNIA_ARCH"
OMNIA_PULP_PLATFORM_PATH="$OMNIA_ARCH/rhel/10.0"
}
""")
    (scripts / "benchmark_tools.list").write_text(
        (TEMPLATES / "benchmark_tools.list.j2").read_text()
    )
    archive = tmp_path / "sample.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        info = tarfile.TarInfo("README")
        info.size = 5
        bundle.addfile(info, io.BytesIO(b"hello"))
    binary = tmp_path / "bin"
    binary.mkdir()
    wget = binary / "wget"
    wget.write_text("""#!/bin/bash
set -eu
while [ "$1" != '-P' ]; do shift; done
mkdir -p "$2"
printf '%s\\n' "$2" >> "$TEST_CALLS"
sleep 0.15
if [ "${TEST_FAIL:-no}" = yes ]; then exit 1; fi
cp "$TEST_ARCHIVE" "$2/source.tar.gz"
""")
    wget.chmod(0o755)
    env = {
        **os.environ,
        "PATH": str(binary) + ":" + os.environ["PATH"],
        "OMNIA_HPC_TOOLS_DIR": str(tmp_path),
        "OMNIA_BENCHMARK_LOGFILE": str(tmp_path / "pull.log"),
        "OMNIA_BENCHMARK_LOCK_TIMEOUT": "10",
        "TEST_ARCHIVE": str(archive),
        "TEST_CALLS": str(tmp_path / "calls"),
    }
    return script, env, tmp_path


def run_pull(downloader):
    """Execute the rendered downloader with bounded local fixture transport."""
    script, env, _root = downloader
    return subprocess.run(
        [str(script)], env=env, capture_output=True, text=True, check=False, timeout=20
    )


@pytest.mark.parametrize("arch,count", [("x86_64", 7), ("aarch64", 6)])
def test_all_tools_download_then_rerun_without_changes(downloader, arch, count):
    """ORCH_UT_045: Both architectures preserve archive bytes, size, and nanosecond mtime."""
    _script, env, root = downloader
    env["TEST_ARCH"] = arch
    first = run_pull(downloader)
    assert first.returncode == 0, first.stdout + first.stderr
    files = sorted((root / "platforms").rglob("*.tar.gz"))
    before = {str(path): (path.read_bytes(), path.stat().st_mtime_ns) for path in files}
    assert len(files) == count
    second = run_pull(downloader)
    assert second.returncode == 0, second.stdout + second.stderr
    assert len((root / "calls").read_text().splitlines()) == count
    assert before == {
        str(path): (path.read_bytes(), path.stat().st_mtime_ns) for path in files
    }
    assert not list(root.rglob(".pull_benchmarks.lock"))


def test_concurrent_pulls_download_each_tool_once(downloader):
    """ORCH_UT_046: Two script processes must share one download, without duplicate writes."""
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(run_pull, downloader) for _ in range(2)]
        results = [future.result() for future in futures]
    assert all(result.returncode == 0 for result in results)
    assert sorted(
        result.stdout.count("[INFO] Pulling from Pulp mirror...") for result in results
    ) == [0, 7]
    assert len((downloader[2] / "calls").read_text().splitlines()) == 7
    assert not list(downloader[2].rglob(".pull_benchmarks.lock"))


def test_corrupt_archive_is_not_reported_as_idempotent(downloader):
    """ORCH_UT_047: An existing invalid archive must fail, while preserving the evidence."""
    assert run_pull(downloader).returncode == 0
    archive = next((downloader[2] / "platforms").rglob("*.tar.gz"))
    archive.write_bytes(b"broken")
    result = run_pull(downloader)
    assert result.returncode == 1
    assert "Invalid or incomplete" in result.stdout
    assert archive.read_bytes() == b"broken"
    assert not list(downloader[2].rglob(".pull_benchmarks.lock"))


def test_failed_download_releases_lock(downloader):
    """ORCH_UT_048: A transport failure must not strand a lock or claim success."""
    downloader[1]["TEST_FAIL"] = "yes"
    assert run_pull(downloader).returncode == 1
    assert not list(downloader[2].rglob(".pull_benchmarks.lock"))


@pytest.mark.parametrize(
    "parent,bound",
    [
        (
            "server:/wrong nfs4 /mnt/vast",
            "server:/wrong[/slurm/hpc_tools] nfs4 /hpc_tools",
        ),
        ("server:/export ext4 /mnt/vast", "/dev/sda ext4 /hpc_tools"),
        ("server:/export nfs4 /mnt/other", "server:/export nfs4 /hpc_tools"),
        ("server:/export nfs4 /mnt/vast", "server:/export nfs4 /"),
    ],
)
def test_wrong_mount_is_rejected(parent, bound):
    """ORCH_UT_049: Do not accept the wrong export, mount target, or local filesystem."""
    output = "\n".join([parent, bound, "rhel|10.0|x86_64", " ".join(BENCHMARK_TOOLS)])
    with pytest.raises(ValueError):
        benchmark._parse_probe(output, "server:/export", "/mnt/vast")


def test_expected_nfs_bind_mount_is_accepted():
    """ORCH_UT_050: NFS subdirectory bind mounts are valid and retain platform identity."""
    output = "\n".join(
        [
            "server:/export nfs4 /mnt/vast",
            "server:/export[/slurm/hpc_tools] nfs4 /hpc_tools",
            "rhel|10.0|aarch64",
            " ".join(BENCHMARK_TOOLS),
        ]
    )
    assert benchmark._parse_probe(output, "server:/export", "/mnt/vast") == (
        "rhel",
        "10.0",
        "aarch64",
    )


def test_vast_storage_and_blank_fallback():
    """ORCH_UT_051: Resolve the HPC export, which may differ from Slurm config storage."""
    context = {
        "storage_config": {
            "mounts": [
                {"name": "vast", "source": "server:/vast", "mount_point": "/vast"},
                {"name": "slurm", "source": "server:/slurm", "mount_point": "/slurm"},
            ]
        }
    }
    assert benchmark._storage(
        context, {"vast_storage_name": "vast", "nfs_storage_name": "slurm"}
    ) == ("server:/vast", "/vast")
    assert benchmark._storage(
        context, {"vast_storage_name": " ", "nfs_storage_name": "slurm"}
    ) == ("server:/slurm", "/slurm")


@pytest.mark.parametrize("cleanup", [True, False])
def test_cleanup_setting_preserves_logs_and_unrelated_tools(
    tmp_path, monkeypatch, cleanup
):
    """ORCH_UT_052: Run the real cleanup shell against an owned temporary workspace."""
    workspace = tmp_path / "benchmark-0123456789abcdef"
    workspace.mkdir()
    (workspace / ".fvt-owned").touch()
    (workspace / "download.log").write_text("download evidence")
    (workspace / "tool.tar.gz").write_bytes(b"tool")
    existing = tmp_path / "existing-tool"
    existing.write_text("keep")
    monkeypatch.setattr(benchmark, "_WORKSPACE", re.compile(re.escape(str(workspace))))

    def local(_host, _row, command):
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, check=False
        )
        return SimpleNamespace(
            rc=result.returncode, stdout=result.stdout, stderr=result.stderr
        )

    monkeypatch.setattr(benchmark, "remote_command", local)
    fields = []
    benchmark._finish(
        None,
        {"HOSTNAME": "compute"},
        str(workspace),
        {"report_path": str(tmp_path / "reports"), "cleanup_benchmark_tools": cleanup},
        fields,
    )
    assert workspace.exists() is not cleanup
    assert existing.read_text() == "keep"
    assert (
        "download evidence" in next((tmp_path / "reports").rglob("*.log")).read_text()
    )


@pytest.mark.parametrize(
    "workspace", ["/hpc_tools", "/hpc_tools/.omnia_fvt/../platforms", "/tmp/tools"]
)
def test_cleanup_rejects_unowned_paths(workspace):
    """ORCH_UT_053: Deletion is restricted to the generated workspace naming contract."""
    with pytest.raises(ValueError):
        benchmark._validate_workspace(workspace)


def test_missing_prerequisite_never_starts_download(monkeypatch):
    """ORCH_UT_054: A direct download selection still enforces the initial mount check."""
    monkeypatch.setattr(benchmark, "marker_is_authorized", lambda _marker: True)
    monkeypatch.setattr(
        benchmark, "load_test_config", lambda: {"report_path": "/tmp/reports"}
    )

    def missing(_host):
        raise RuntimeError("mount missing")

    monkeypatch.setattr(benchmark, "_preconditions", missing)
    monkeypatch.setattr(
        benchmark, "_prepare", lambda *_args: pytest.fail("download attempted")
    )
    result = benchmark.check_slurm_benchmark_idempotency(None)
    assert not result["success"]
    assert "mount missing" in result["error"]


def test_failed_check_still_finalizes_and_keeps_original_error(monkeypatch):
    """ORCH_UT_055: Both test failure and cleanup failure must remain visible."""
    monkeypatch.setattr(benchmark, "marker_is_authorized", lambda _marker: True)
    monkeypatch.setattr(
        benchmark, "load_test_config", lambda: {"report_path": "/tmp/reports"}
    )
    row = {"HOSTNAME": "compute"}
    monkeypatch.setattr(benchmark, "_preconditions", lambda _host: ([row], {}, []))
    monkeypatch.setattr(benchmark, "_prepare", lambda *_args: None)

    def failed_check(*_args):
        raise RuntimeError("download failed")

    def failed_cleanup(*_args):
        raise RuntimeError("cleanup failed")

    monkeypatch.setattr(benchmark, "_idempotency", failed_check)
    monkeypatch.setattr(benchmark, "_finish", failed_cleanup)
    result = benchmark.check_slurm_benchmark_idempotency(None)
    assert not result["success"]
    assert "download failed" in result["error"] and "cleanup failed" in result["error"]


@pytest.mark.parametrize("invalid", ["false", 0, None])
def test_invalid_cleanup_config_fails_before_remote_access(monkeypatch, invalid):
    """ORCH_UT_056: YAML booleans are required rather than truthy strings or numbers."""
    monkeypatch.setattr(benchmark, "marker_is_authorized", lambda _marker: True)
    monkeypatch.setattr(
        benchmark, "load_test_config", lambda: {"cleanup_benchmark_tools": invalid}
    )
    monkeypatch.setattr(
        benchmark, "_preconditions", lambda *_args: pytest.fail("remote access")
    )
    assert not benchmark.check_slurm_benchmark_idempotency(None)["success"]


def test_fvt_idempotency_uses_real_snapshot_and_downloader(downloader, monkeypatch):
    """ORCH_UT_057: Exercise the FVT pull/snapshot integration, including remote shell

    quoting.
    """
    _script, environment, root = downloader
    monkeypatch.setattr(benchmark, "_WORKSPACE", re.compile(re.escape(str(root))))

    def remote(_host, _row, command):
        result = subprocess.run(
            command,
            shell=True,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
        return SimpleNamespace(
            rc=result.returncode, stdout=result.stdout, stderr=result.stderr
        )

    monkeypatch.setattr(benchmark, "remote_command", remote)
    row = {"HOSTNAME": "compute"}
    fields = []
    benchmark._idempotency(
        None,
        [row],
        {"compute": ("rhel", "10.0", "x86_64")},
        str(root),
        fields,
    )
    assert any("7 tools; 7 valid archives" in value for _key, value in fields)
    presence = [value for key, value in fields if key.startswith("Archive presence")]
    assert len(presence) == 7
    for tool in BENCHMARK_TOOLS:
        assert any(
            f"/{tool}/source.tar.gz" in value
            and "PRESENT" in value
            and "tar integrity passed" in value
            for value in presence
        )
    assert len((root / "calls").read_text().splitlines()) == 7


def test_log_save_failure_retains_tools(tmp_path, monkeypatch):
    """ORCH_UT_058: Do not delete the only diagnostic copy if logs cannot be collected."""
    workspace = "/hpc_tools/.omnia_fvt/benchmark-0123456789abcdef"
    calls = []

    def unavailable(_host, _row, script):
        calls.append(script)
        raise RuntimeError("SSH log read failed")

    monkeypatch.setattr(benchmark, "_run", unavailable)
    with pytest.raises(RuntimeError, match="SSH log read failed"):
        benchmark._finish(None, {}, workspace, {"report_path": str(tmp_path)}, [])
    assert len(calls) == 1
    assert "-delete" not in calls[0]


@pytest.mark.parametrize("state", ["missing", "empty", "corrupt", "symlink"])
def test_archive_presence_rejects_missing_or_invalid_files(tmp_path, state):
    """ORCH_UT_059: File presence requires a real, non-empty, valid tool archive."""
    directory = tmp_path / "imb"
    directory.mkdir()
    archive = directory / "source.tar.gz"
    if state == "empty":
        archive.touch()
    elif state == "corrupt":
        archive.write_bytes(b"not a tarball")
    elif state == "symlink":
        archive.symlink_to(tmp_path / "absent.tar.gz")
    result = subprocess.run(
        ["python3", "-c", BENCHMARK_SNAPSHOT_SCRIPT, str(tmp_path), "imb"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert result.stdout == ""
    reason = {
        "missing": "Missing benchmark archives",
        "empty": "Empty archive",
        "corrupt": "Corrupt archive",
        "symlink": "Symlink archive is not allowed",
    }[state]
    assert reason in result.stderr
    assert str(directory if state == "missing" else archive) in result.stderr


@pytest.mark.parametrize("state", ["unmounted", "wrong_export"])
def test_script_check_waits_for_valid_mount(monkeypatch, state):
    """ORCH_UT_060: A failed mount must stop before checking shared scripts."""
    commands = []

    def remote(_host, _row, script):
        commands.append(script)
        if state == "unmounted":
            raise RuntimeError("MOUNT FAILED: /hpc_tools is not mounted")
        return "server:/wrong nfs4 /mnt/vast\nserver:/wrong nfs4 /hpc_tools\n"

    monkeypatch.setattr(benchmark, "_run", remote)
    with pytest.raises((RuntimeError, ValueError), match="MOUNT FAILED"):
        benchmark._probe(None, {"HOSTNAME": "compute"}, "server:/export", "/mnt/vast")
    assert len(commands) == 1
    assert "test -f /hpc_tools/scripts/pull_benchmarks.sh" not in commands[0]


@pytest.mark.parametrize(
    "state,expected",
    [
        ("missing", "MISSING"),
        ("empty", "EMPTY"),
        ("not_executable", "NOT EXECUTABLE"),
        ("invalid", "INVALID BASH SYNTAX"),
        ("valid", ""),
    ],
)
def test_deployed_pull_script_presence_check(tmp_path, state, expected):
    """ORCH_UT_061: Inspect the real file, execute permission, and Bash syntax."""
    script = tmp_path / "pull_benchmarks.sh"
    if state != "missing":
        contents = {"empty": "", "invalid": "if then\n"}.get(
            state, "#!/bin/bash\ntrue\n"
        )
        script.write_text(contents)
        script.chmod(0o644 if state == "not_executable" else 0o755)
    command = (
        BENCHMARK_COMMANDS["script_probe"]
        .format()
        .replace("/hpc_tools/scripts/pull_benchmarks.sh", shlex.quote(str(script)))
    )
    result = subprocess.run(
        ["bash", "-c", command], capture_output=True, text=True, check=False
    )
    assert (result.returncode == 0) == (state == "valid")
    if expected:
        assert expected in result.stderr
        assert "pull_benchmarks.sh" in result.stderr


def test_missing_pull_script_fails_prerequisites_and_blocks_download(monkeypatch):
    """ORCH_UT_062: A mounted share without the pull script cannot start FVT downloads."""
    row = {
        "HOSTNAME": "compute",
        "EXPECTED_FUNCTIONAL_GROUP": "slurm_node_rhel_10_0_x86_64",
    }
    context = {
        "storage_config": {
            "mounts": [
                {
                    "name": "shared",
                    "source": "server:/export",
                    "mount_point": "/mnt/vast",
                }
            ]
        }
    }
    monkeypatch.setattr(
        benchmark,
        "slurm_context",
        lambda _host: (context, [row], None, {"nfs_storage_name": "shared"}),
    )

    def remote(_host, _row, script):
        if script == BENCHMARK_COMMANDS["mount_probe"].format(
            expected="/mnt/vast/slurm/hpc_tools", mount="/mnt/vast"
        ):
            return "server:/export nfs4 /mnt/vast\nserver:/export nfs4 /hpc_tools\n"
        assert script == BENCHMARK_COMMANDS["script_probe"].format()
        raise RuntimeError(
            "MISSING: /hpc_tools/scripts/pull_benchmarks.sh (mount check passed)"
        )

    monkeypatch.setattr(benchmark, "_run", remote)
    result = benchmark.check_slurm_benchmark_prerequisites(None)
    assert not result["success"]
    assert "compute" in result["error"] and "MISSING" in result["error"]
    monkeypatch.setattr(benchmark, "marker_is_authorized", lambda _marker: True)
    monkeypatch.setattr(
        benchmark, "load_test_config", lambda: {"report_path": "/tmp/reports"}
    )
    monkeypatch.setattr(
        benchmark, "_prepare", lambda *_args: pytest.fail("download attempted")
    )
    assert not benchmark.check_slurm_benchmark_idempotency(None)["success"]


def test_prerequisite_report_names_the_pull_script(monkeypatch):
    """ORCH_UT_063: Successful prerequisites explicitly report the deployed pull file."""
    row = {
        "HOSTNAME": "compute",
        "EXPECTED_FUNCTIONAL_GROUP": "slurm_node_rhel_10_0_x86_64",
    }
    context = {
        "storage_config": {
            "mounts": [
                {
                    "name": "shared",
                    "source": "server:/export",
                    "mount_point": "/mnt/vast",
                }
            ]
        }
    }
    monkeypatch.setattr(
        benchmark,
        "slurm_context",
        lambda _host: (context, [row], None, {"nfs_storage_name": "shared"}),
    )
    monkeypatch.setattr(benchmark, "_probe", lambda *_args: ("rhel", "10.0", "x86_64"))
    result = benchmark.check_slurm_benchmark_prerequisites(None)
    assert result["success"]
    fields = dict(result["details"]["fields"])
    assert fields["compute mount"].startswith("PASS")
    assert fields["compute pull_benchmarks.sh"] == (
        "PRESENT | /hpc_tools/scripts/pull_benchmarks.sh | executable | bash syntax passed"
    )


@pytest.mark.parametrize(
    "fault",
    ["checksum", "size", "mtime", "redownload", "incomplete_first", "missing", "added"],
)
def test_idempotency_rejects_changed_files_or_download_counts(monkeypatch, fault):
    """ORCH_UT_064: Changed archives or unexpected downloads must fail the check."""
    row = {"HOSTNAME": "compute"}
    platform = ("rhel", "10.0", "x86_64")
    before = {"imb/source.tar.gz": ["original-sha256", 100, 123456789]}
    after = {name: list(metadata) for name, metadata in before.items()}
    if fault in ("checksum", "size", "mtime"):
        index = {"checksum": 0, "size": 1, "mtime": 2}[fault]
        after["imb/source.tar.gz"][index] = "changed" if index == 0 else 999
    elif fault == "missing":
        after.clear()
    elif fault == "added":
        after["imb/extra.tar.gz"] = ["new-sha256", 100, 123456789]
    download_line = "[INFO] Pulling from Pulp mirror...\n"
    outputs = iter(
        [
            download_line * (6 if fault == "incomplete_first" else 7),
            download_line if fault == "redownload" else "",
        ]
    )
    snapshots = iter([before, after])
    monkeypatch.setattr(benchmark, "_pull", lambda *_args: next(outputs))
    monkeypatch.setattr(benchmark, "_snapshot", lambda *_args: next(snapshots))
    with pytest.raises(RuntimeError, match="Download/idempotency failed") as caught:
        benchmark._idempotency(
            None, [row], {"compute": platform}, "/unused-workspace", []
        )
    expected_reason = {
        "checksum": "imb/source.tar.gz: SHA-256 changed; expected original-sha256, actual changed",
        "size": "imb/source.tar.gz: size (bytes) changed; expected 100, actual 999",
        "mtime": "imb/source.tar.gz: mtime (ns) changed; expected 123456789, actual 999",
        "redownload": "rerun downloads: expected 0, actual 1",
        "incomplete_first": "initial downloads: expected 7, actual 6",
        "missing": "archive missing: imb/source.tar.gz",
        "added": "unexpected archive: imb/extra.tar.gz",
    }[fault]
    assert expected_reason in str(caught.value)
    assert "compute" in str(caught.value) and "rhel/10.0/x86_64" in str(caught.value)
    assert "/unused-workspace" in str(caught.value)


@pytest.mark.parametrize(
    "counts,different_files",
    [([7, 7], False), ([0, 0], False), ([6, 0], False), ([7, 0], True)],
    ids=["duplicate_downloads", "no_downloads", "partial_download", "different_files"],
)
def test_concurrency_rejects_duplicate_or_inconsistent_results(
    monkeypatch, counts, different_files
):
    """ORCH_UT_065: Two peers must download exactly once and see identical files."""
    rows = [{"HOSTNAME": "first"}, {"HOSTNAME": "second"}]
    platform = ("rhel", "10.0", "x86_64")

    def pull(_host, row, *_args):
        index = 0 if row["HOSTNAME"] == "first" else 1
        return "[INFO] Pulling from Pulp mirror...\n" * counts[index]

    def snapshot(_host, row, *_args):
        checksum = "different" if different_files and row == rows[1] else "same"
        return {"imb/source.tar.gz": [checksum, 100, 123456789]}

    monkeypatch.setattr(benchmark, "_pull", pull)
    monkeypatch.setattr(benchmark, "_snapshot", snapshot)
    with pytest.raises(
        RuntimeError, match="did not reuse one shared download"
    ) as caught:
        benchmark._concurrency(
            None, rows, {row["HOSTNAME"]: platform for row in rows}, "/unused", []
        )
    error = str(caught.value)
    assert "expected=first, actual=second" in error
    if different_files:
        assert (
            "imb/source.tar.gz: SHA-256 changed; expected same, actual different"
            in error
        )
    else:
        assert "expected one node to download 7 tools and the other 0" in error
        assert f"actual: first={counts[0]}, second={counts[1]}" in error


def test_command_failure_preserves_downloader_error_and_stderr(monkeypatch):
    """ORCH_UT_066: Transport stderr must not hide the downloader's error reason."""
    monkeypatch.setattr(
        benchmark,
        "remote_command",
        lambda *_args: SimpleNamespace(
            rc=1,
            stdout="[ERROR] Invalid or incomplete benchmark content: /tools/imb",
            stderr="wget: connection refused",
        ),
    )
    with pytest.raises(RuntimeError) as caught:
        benchmark._run(None, {"HOSTNAME": "compute"}, "unused")
    error = str(caught.value)
    assert "compute: command failed (rc=1)" in error
    assert "Invalid or incomplete benchmark content: /tools/imb" in error
    assert "wget: connection refused" in error
