#!/usr/bin/env bash
# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "${SCRIPT_DIR}")"
VENV_PYTHON="${PARENT_DIR}/.venv/bin/python3"

export OMNIA_TEST_MODULE_ROOT="${SCRIPT_DIR}"
export OMNIA_TEST_CONFIG_FILE="test_config.yml"
export OMNIA_TEST_CREDENTIALS_FILE="test_creds.yml"
export OMNIA_TEST_CREDENTIALS_KEY=".test_creds.key"
export PYTHONPATH="${PARENT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"

if [[ -x "${VENV_PYTHON}" ]]; then
    PYTHON_BIN="${VENV_PYTHON}"
else
    PYTHON_BIN="$(command -v python3)"
fi

exec "${PYTHON_BIN}" "${SCRIPT_DIR}/_run.py" "$@"
