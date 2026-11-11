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

"""Dependency-free classifiers for cleanup inspection commands."""

PATH_EXISTS = "exists"
PATH_ABSENT = "absent"
INSPECTION_ERROR = "error"


def classify_path_probe(return_code, output):
    """Classify a shell ``test`` result without hiding command failures."""
    normalized_output = (output or "").strip()
    if return_code == 0 and normalized_output == PATH_EXISTS:
        return PATH_EXISTS
    if return_code == 1 and not normalized_output:
        return PATH_ABSENT
    return INSPECTION_ERROR


def is_expected_stopped_state(return_code, status):
    """Return whether systemctl explicitly reported a stopped/absent unit."""
    return (return_code, status) in {
        (3, "inactive"),
        (3, "failed"),
        (4, "unknown"),
        (4, "not-found"),
    }


def is_expected_disabled_state(return_code, status):
    """Return whether systemctl explicitly reported a disabled/absent unit."""
    return (return_code, status) in {
        (1, "disabled"),
        (1, "not-found"),
    }
