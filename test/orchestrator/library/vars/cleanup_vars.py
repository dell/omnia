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

"""Immutable contracts for full Orchestrator cleanup verification."""

CLEANUP_EXTRA_VARIABLES: tuple[str, ...] = (
    "cleanup_credentials",
    "cleanup_slurm",
    "cleanup_k8s",
)

OPENCHAMI_CLEANUP_CONTAINERS: tuple[str, ...] = (
    "boot-service",
    "coresmd-coredhcp",
    "coresmd-coredns",
    "haproxy",
    "metadata-service",
    "postgres",
    "smd",
    "smd-init",
    "step-ca",
    "tokensmith",
)

OPENCHAMI_CLEANUP_UNITS: tuple[str, ...] = (
    "openchami.target",
    "acme-deploy.service",
    "acme-register.service",
    "boot-service.service",
    "coresmd-coredhcp.service",
    "coresmd-coredns.service",
    "haproxy.service",
    "metadata-service.service",
    "openchami-cert-trust.service",
    "postgres.service",
    "smd-init.service",
    "smd.service",
    "step-ca.service",
    "tokensmith.service",
)

OPENCHAMI_CLEANUP_VOLUMES: tuple[str, ...] = (
    "boot-service-data",
    "metadata-service-data",
    "postgres-data",
)

OPENCHAMI_CLEANUP_PACKAGES: tuple[str, ...] = ("openchami", "ochami")

OPENCHAMI_STATIC_PATHS: tuple[str, ...] = (
    "/etc/openchami",
    "/etc/ochami",
)

OPENLDAP_SERVICE = "omnia_auth.service"
OPENLDAP_CONTAINER = "omnia_auth"
OPENLDAP_QUADLET = "/etc/containers/systemd/omnia_auth.container"

PRESERVED_INPUT_FILES: tuple[str, ...] = (
    "omnia_config.yml",
    "orchestrator_config.yml",
    "network_spec.yml",
    "storage_config.yml",
)

CREDENTIAL_FILES: tuple[str, ...] = (
    "orchestrator_credentials.yml",
    ".orchestrator_credentials_key",
    "orchestrator_credentials.yml.lock",
    ".orchestrator_credentials_key.lock",
)
