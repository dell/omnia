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
Image Build Manager — Variables

Common constants, paths, container names, and command templates.
"""

from .common_vars import (
    MODULE_ROOT,
    MONOREPO_ROOT,
    SRC_INPUT_DIR,
    SRC_REPO_OUTPUT_DIR,
    SHARED_PATH,
    MINIO_CONTAINER,
    REGISTRY_CONTAINER,
    REGISTRY_PORT,
    S3_EXPECTED_BUCKETS,
    S3CMD_CONFIG_PATH,
    IMAGE_TYPES,
    IMAGE_TYPE_DISPLAY,
    PLAYBOOK_TAGS,
    PLAYBOOK_ENTRY_POINT,
    PLAYBOOK_WORKDIR,
    CMDS,
    DOMAIN_NAME,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    IBM_CONFIG_FILE,
    FIREWALL_PORTS,
    LISTENING_PORTS,
    SYSTEMD_SERVICES,
    CREDENTIALS_FILE_NAME,
    CREDENTIALS_KEY_NAME,
    BUILD_STATUS_PATH,
    BUILD_LOG_PATH,
    PLAYBOOK_CMD,
    FG_PACKAGES_FILENAME,
    IMAGE_VERIFY_TEMP_IMAGE,
    IMAGE_VERIFY_TEMP_MOUNT,
    SQUASHFS_PACKAGE,
    S3_BOOT_IMAGES_BUCKET,
    IPV4_PATTERN,
    REQUIRED_CONFIG_FIELDS,
    REQUIRED_DATASET_FILES,
    REQUIRED_SRC_FILES,
)

from .test_case_vars import TEST_CASES

from .domain_vars import (
    DOMAIN_NAME as VALIDATION_DOMAIN,
    FVT_TAGS,
    MARKERS,
    SUITES,
    EXCLUDE_TAGS,
)
