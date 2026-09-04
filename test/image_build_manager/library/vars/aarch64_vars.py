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

"""AArch64 build-node constants and remote probe commands."""

AARCH64_EXPECTED_ARCHITECTURE = "aarch64"
AARCH64_SSH_USER = "root"
AARCH64_WORK_SUBDIRS = (
    "",
    "openchami/aarch64",
    "workdir",
    "log",
)

# Commands executed on the optional AArch64 build node.
AARCH64_CMDS = {
    "aarch64_ssh_test": "echo OK",
    "aarch64_uname": "uname -m; uname -s; uname -r",
    "aarch64_test_dir": "test -d {path} && echo exists",
    "aarch64_podman_version": "podman --version",
    "aarch64_builder_images": (
        "podman images --format '{{.Repository}}:{{.Tag}}' "
        "| grep -E 'aarch64-image-(builder|thrillhouse)'"
    ),
    "aarch64_regctl_version": "/usr/local/bin/regctl version",
}
