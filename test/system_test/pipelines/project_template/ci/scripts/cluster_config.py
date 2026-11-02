#!/usr/bin/env python3
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

"""Print one validated value of clusters/<cluster>/cluster.yml (for remote_stage.sh).

    python3 ci/scripts/cluster_config.py <cluster> <key>

Every value printed was validated by svt_ci.load_cluster (fixed character
sets), so the shell can use it without further parsing.
"""

import sys

from svt_ci import ConfigError, load_cluster, load_theme


def main(argv) -> int:
    """Print the value or a theme key (theme:<theme>:<key>)."""
    if len(argv) != 2:
        print("usage: cluster_config.py <cluster>|theme:<theme> <key>", file=sys.stderr)
        return 2
    try:
        if argv[0].startswith("theme:"):
            data = load_theme(argv[0].split(":", 1)[1])
        else:
            data = load_cluster(argv[0])
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    value = data.get(argv[1])
    if value is None:
        print(f"ERROR: unknown key {argv[1]!r}", file=sys.stderr)
        return 2
    print(" ".join(map(str, value)) if isinstance(value, list) else value)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
