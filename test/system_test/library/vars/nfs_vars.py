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

"""Constants of the NFS share cleanup (library/functions/nfs_func.py)."""

import re

HOST_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"

HOST_RE = re.compile(rf"{HOST_LABEL}(?:\.{HOST_LABEL})*")

IPV4_RE = re.compile(r"(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})")

EXPORT_RE = re.compile(r"/[A-Za-z0-9_.@+=:-]+(?:/[A-Za-z0-9_.@+=:-]+)*")

# The deny list of omnia.sh safe_rm_dir: never emptied, whatever the share is called.
DENIED_EXPORTS = frozenset({"/", "/boot", "/dev", "/etc", "/home", "/media", "/mnt", "/opt",
                            "/proc", "/root", "/run", "/srv", "/sys", "/tmp",  # nosec B108
                            "/usr", "/var"})  # a deny list entry, never used as a path

MOUNT_OPTIONS = "nosuid,nodev,noexec,soft,timeo=100,retrans=3"

COMMAND_ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"}

MOUNT_TIMEOUT = 180

UNMOUNT_TIMEOUT = 120

MAX_DEPTH = 64

MAX_ERRORS = 20

MOUNT_ROOT = "/run"
