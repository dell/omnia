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

# pylint: disable=too-few-public-methods
"""Controlled compatibility adapter for ``ochami discover static``."""

import os
import subprocess

from .client import OpenChamiError


class DiscoveryError(OpenChamiError):
    """Raised when static discovery fails."""


class StaticDiscovery:
    """Invoke the supported Go discovery implementation without a shell."""

    def __init__(self, binary="/usr/bin/ochami", timeout=120):
        self.binary = binary
        self.timeout = timeout

    def run(self, nodes_file, access_token, token_env_key, cluster_uri, ca_cert=None):
        """Run static discovery with an explicit gateway and trust anchor."""
        nodes_file = os.path.realpath(nodes_file)
        if not os.path.isfile(nodes_file):
            raise DiscoveryError(f"OpenCHAMI nodes file does not exist: {nodes_file}")
        if not token_env_key or not str(token_env_key).endswith("_ACCESS_TOKEN"):
            raise DiscoveryError("A valid OpenCHAMI access-token environment key is required")
        environment = os.environ.copy()
        environment[str(token_env_key)] = access_token
        command = [self.binary, "--cluster-uri", cluster_uri]
        if ca_cert:
            command.extend(("--cacert", ca_cert))
        command.extend(
            (
                "discover",
                "static",
                "--overwrite",
                "-f",
                "yaml",
                "-d",
                "@" + nodes_file,
            )
        )
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=environment,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise DiscoveryError(f"Unable to execute static discovery: {exc}") from exc
        finally:
            environment.pop(str(token_env_key), None)

        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "no error output").strip()
            raise DiscoveryError(
                f"ochami static discovery exited with {completed.returncode}: {detail[:2000]}"
            )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
        }
