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

"""Immutable Slurm benchmark FVT paths, tools, timeouts, and node commands.

Named command placeholders are populated only by the verification helper.
Shell arguments must be quoted or constrained by workspace validation before
formatting; doubled braces are literal shell/awk braces.
"""

BENCHMARK_TOOLS_ROOT = "/hpc_tools"
BENCHMARK_TOOLS: tuple[str, ...] = (
    "osu-micro-benchmarks",
    "imb",
    "likwid",
    "papi",
    "geopm",
    "sionlib",
    "msr-safe",
)
BENCHMARK_DOWNLOAD_TIMEOUT_SECONDS = 1800
BENCHMARK_LOCK_TIMEOUT_SECONDS = BENCHMARK_DOWNLOAD_TIMEOUT_SECONDS - 30
BENCHMARK_BARRIER_TIMEOUT_SECONDS = 60
BENCHMARK_WORKSPACE_PATTERN = r"/hpc_tools/\.omnia_fvt/benchmark-[a-f0-9]{16}"

# Inspect each downloaded archive without extracting it on the compute node.
BENCHMARK_SNAPSHOT_SCRIPT = r"""
import hashlib, json, pathlib, subprocess, sys
root = pathlib.Path(sys.argv[1])
result = {}
for tool in sys.argv[2:]:
    directory = root / tool
    archives = sorted(directory.glob('*.tar.gz'))
    if not archives:
        raise RuntimeError('Missing benchmark archives: expected *.tar.gz in ' + str(directory))
    for archive in archives:
        if archive.is_symlink():
            raise RuntimeError('Symlink archive is not allowed: ' + str(archive))
        if not archive.is_file():
            raise RuntimeError('Archive is not a regular file: ' + str(archive))
        if archive.stat().st_size == 0:
            raise RuntimeError('Empty archive: ' + str(archive))
        check = subprocess.run(['tar', '-tzf', str(archive)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if check.returncode:
            raise RuntimeError('Corrupt archive: ' + str(archive) + ': ' + check.stderr.strip()[-500:])
        with archive.open('rb') as stream:
            checksum = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                checksum.update(chunk)
            digest = checksum.hexdigest()
        stat = archive.stat()
        result[str(archive.relative_to(root))] = [digest, stat.st_size, stat.st_mtime_ns]
if (root / '.pull_benchmarks.lock').exists():
    raise RuntimeError('Downloader left a lock behind: ' + str(root / '.pull_benchmarks.lock'))
print(json.dumps(result, sort_keys=True))
"""


BENCHMARK_COMMANDS: dict[str, str] = {
    "shell": "bash -c {script}",
    "snapshot": "python3 -c {script} {args}",
    "mount_probe": """set -eu
mountpoint -q {mount} || {{
    printf 'MOUNT FAILED: configured storage mount is unavailable: %s\\n' {mount} >&2
    exit 1
}}
mountpoint -q /hpc_tools || {{
    echo 'MOUNT FAILED: /hpc_tools is not mounted; cannot verify pull_benchmarks.sh' >&2
    exit 1
}}
test {expected} -ef /hpc_tools || {{
    printf 'MOUNT FAILED: /hpc_tools does not match expected bind source: %s\\n' {expected} >&2
    exit 1
}}
findmnt -rn -M {mount} -o SOURCE,FSTYPE,TARGET
findmnt -rn -M /hpc_tools -o SOURCE,FSTYPE,TARGET
""",
    "script_probe": """set -eu
test -f /hpc_tools/scripts/pull_benchmarks.sh || {{
    echo 'MISSING: /hpc_tools/scripts/pull_benchmarks.sh (mount check passed)' >&2
    exit 1
}}
test -s /hpc_tools/scripts/pull_benchmarks.sh || {{
    echo 'EMPTY: /hpc_tools/scripts/pull_benchmarks.sh' >&2
    exit 1
}}
test -x /hpc_tools/scripts/pull_benchmarks.sh || {{
    echo 'NOT EXECUTABLE: /hpc_tools/scripts/pull_benchmarks.sh' >&2
    exit 1
}}
bash -n /hpc_tools/scripts/pull_benchmarks.sh || {{
    echo 'INVALID BASH SYNTAX: /hpc_tools/scripts/pull_benchmarks.sh' >&2
    exit 1
}}
""",
    "probe": """set -euE
trap 'echo "Benchmark prerequisite failed: $BASH_COMMAND" >&2' ERR
test -r /hpc_tools/scripts/omnia_platform.sh
test -r /hpc_tools/scripts/benchmark_tools.list
bash -n /hpc_tools/scripts/omnia_platform.sh
unset OMNIA_TEST_ARCH OMNIA_HPC_TOOLS_DIR
. /etc/os-release
actual_os="$ID"; actual_version="$VERSION_ID"; actual_arch="$(uname -m)"
. /hpc_tools/scripts/omnia_platform.sh
omnia_detect_platform
test "$OMNIA_OS_TYPE" = "$actual_os"
test "$OMNIA_OS_VERSION" = "$actual_version"
test "$OMNIA_ARCH" = "$actual_arch"
test "$OMNIA_PLATFORM_ROOT" = "/hpc_tools/platforms/$actual_os/$actual_version/$actual_arch"
printf '%s|%s|%s\\n' "$OMNIA_OS_TYPE" "$OMNIA_OS_VERSION" "$OMNIA_ARCH"
awk '!/^[[:space:]]*#/ && NF {{printf "%s ", $1}} END {{print ""}}' \
    /hpc_tools/scripts/benchmark_tools.list
""",
    "prepare": """set -euE
trap 'echo "Benchmark workspace preparation failed: $BASH_COMMAND" >&2' ERR
for feature in OMNIA_BENCHMARK_LOGFILE OMNIA_HPC_TOOLS_DIR .pull_benchmarks.lock; do
    grep -Fq "$feature" /hpc_tools/scripts/pull_benchmarks.sh || {{
        echo 'Redeploy updated pull_benchmarks.sh before download FVT'; exit 1;
    }}
done
command -v python3 >/dev/null
command -v timeout >/dev/null
command -v wget >/dev/null || command -v curl >/dev/null
test ! -L /hpc_tools/.omnia_fvt
mkdir -p /hpc_tools/.omnia_fvt
mkdir -m 0700 {workspace}
touch {workspace}/.fvt-owned
mkdir {workspace}/scripts
cp /hpc_tools/scripts/{{pull_benchmarks.sh,omnia_platform.sh,benchmark_tools.list}} \
    {workspace}/scripts/
""",
    "barrier": """touch {workspace}/ready-{label}
deadline=$((SECONDS + {barrier_timeout}))
while [ "$(find {workspace} -maxdepth 1 -name 'ready-*' | wc -l)" -lt 2 ]; do
    [ "$SECONDS" -lt "$deadline" ] || {{
        echo 'Concurrent download start timed out after {barrier_timeout}s: expected two ready peers in {workspace}' >&2
        exit 1
    }}
    sleep 1
done
""",
    "pull": """set -eu
{wait}timeout --kill-after=10 {download_timeout} env -u OMNIA_TEST_ARCH \
OMNIA_HPC_TOOLS_DIR={workspace} OMNIA_BENCHMARK_LOGFILE={workspace}/{label}.log \
OMNIA_BENCHMARK_LOCK_TIMEOUT={lock_timeout} \
{workspace}/scripts/pull_benchmarks.sh
""",
    "logs": """set -eu
test ! -L /hpc_tools/.omnia_fvt
test ! -L {workspace}
if test -d {workspace}; then
    test -f {workspace}/.fvt-owned
    for log in {workspace}/*.log; do
        test -f "$log" || continue
        printf '\\n--- %s ---\\n' "$log"
        cat "$log"
    done
fi
""",
    "cleanup": """set -eu
test ! -L /hpc_tools/.omnia_fvt
test ! -L {workspace}
if test -d {workspace}; then
    test -f {workspace}/.fvt-owned
    find {workspace} -xdev -depth -mindepth 1 -delete
    rmdir {workspace}
fi
test ! -e {workspace}
""",
}
