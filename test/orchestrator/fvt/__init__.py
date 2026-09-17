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

"""
Functional Verification Tests (FVT) for orchestrator.

Scenarios:
    precheck            — Verify OIM connectivity and environment prerequisites
    validate            — Validate input configuration and OpenCHAMI settings
    prepare             — Deploy infrastructure (OpenCHAMI, OpenLDAP)
    deploy              — Verify OpenCHAMI deployment state
    provision           — Provision Slurm and Kubernetes clusters
    execute             — Execute lifecycle and feature tests
    pxeboot             — PXE boot verification and contracts
    check               — Post-deployment verification (Slurm, Kubernetes, features)
    cleanup             — Clean up all deployed resources
    rollback            — Rollback deployment state
    negative            — Invalid input and error scenario handling
    playbooks           — Source-contract and playbook structure tests
"""
