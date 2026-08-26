#!/usr/bin/env bash
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

# =============================================================================
# image_build_manager — Validation Runner
# =============================================================================
# Delegates to the Python validation runner.  Environment setup (venv,
# baremetal, dependencies) is handled by setup_env.sh — this script
# simply forwards arguments.
#
# Usage:
#   ./run_validation.sh fvt_image_build_manager <tag> <command> [options]
#   ./run_validation.sh fvt_image_build_manager list
#   ./run_validation.sh nft_image_build_manager test
#   ./run_validation.sh --config
#   ./run_validation.sh --help
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python3 "${SCRIPT_DIR}/_run.py" "$@"
