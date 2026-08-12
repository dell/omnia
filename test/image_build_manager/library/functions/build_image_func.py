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
Build Image — Core Verification Functions (re-export hub).

This module was split into smaller, domain-focused files for
maintainability.  All public names are re-exported here so existing
``from .build_image_func import ...`` statements keep working.

Sub-modules:
    _config_helpers      — SSH retry, remote config loading, FG resolution
    container_func       — Podman container checks
    s3_func              — S3 bucket & image verification
    registry_func        — OCI registry verification
    build_status_func    — build_status.yml & functional group checks
    image_content_func   — squashfs mount + RPM package verification
    cleanup_func         — post-cleanup assertions
    precheck_func        — prepare / validate / precheck assertions
    log_func             — build log collection
"""

# --- Config helpers (public) -------------------------------------------------
from ._config_helpers import (                       # noqa: F401
    get_configured_functional_groups,
)

# --- Container checks --------------------------------------------------------
from .container_func import (                        # noqa: F401
    check_container_running,
    check_s3_containers,
)

# --- S3 checks ---------------------------------------------------------------
from .s3_func import (                               # noqa: F401
    check_s3_buckets,
    check_s3_bucket_images,
)

# --- Registry checks ---------------------------------------------------------
from .registry_func import (                         # noqa: F401
    check_registry_images,
)

# --- Build status / functional groups ----------------------------------------
from .build_status_func import (                     # noqa: F401
    check_build_status_file,
    check_functional_groups_built,
)

# --- Image content (squashfs + RPM) ------------------------------------------
from .image_content_func import (                    # noqa: F401
    verify_image_packages,
)

# --- Cleanup verification ----------------------------------------------------
from .cleanup_func import (                          # noqa: F401
    check_containers_removed,
    check_s3_artifacts_removed,
    check_services_removed,
    check_firewall_ports_removed,
    check_s3cfg_removed,
    check_credentials_removed,
    check_build_output_removed,
    check_registry_cleaned,
)

# --- Prepare / validate / precheck -------------------------------------------
from .precheck_func import (                         # noqa: F401
    check_s3cmd_configured,
    check_firewall_ports_open,
    check_services_active,
    check_credentials_present,
    check_clone_status,
    check_registry_reachable,
    check_input_config_exists,
    check_target_connectivity,
    check_env_vars_present,
    check_hostname_domain,
    check_admin_ip,
    check_omnia_setup,
)

# --- Log collection ----------------------------------------------------------
from .log_func import (                              # noqa: F401
    collect_build_logs,
)
