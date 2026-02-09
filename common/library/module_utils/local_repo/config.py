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
#pylint: disable=line-too-long

"""
Consolidated configuration file for Ansible module utilities.
"""

# ----------------------------
# Parallel Tasks Defaults
# Used by  parallel_tasks.py
# ----------------------------
DEFAULT_NTHREADS = 4
DEFAULT_TIMEOUT = 60
LOG_DIR_DEFAULT = "/tmp/thread_logs"
DEFAULT_LOG_FILE = "/tmp/task_results_table.log"
DEFAULT_SLOG_FILE = "/tmp/stask_results_table.log"
CSV_FILE_PATH_DEFAULT = [
    "/tmp/x86_64/status_results_table.csv",
    "/tmp/aarch64/status_results_table.csv"
]
DEFAULT_REPO_STORE_PATH = "/tmp/offline_repo"
USER_JSON_FILE_DEFAULT = ""
DEFAULT_STATUS_FILENAME = "status.csv"
STATUS_CSV_HEADER = 'name,type,status\n'
SOFTWARE_CSV_HEADER = "name,status"
# USER_REG_CRED_INPUT = "/opt/omnia/input/project_default/user_registry_credential.yml"
# USER_REG_KEY_PATH = "/opt/omnia/input/project_default/.local_repo_credentials_key"
# ----------------------------
# Software tasklist Defaults
# Used by prepare_tasklist.py
# ----------------------------
LOCAL_REPO_CONFIG_PATH_DEFAULT = "/opt/omnia/input/project_default/local_repo_config.yml"
SOFTWARE_CONFIG_PATH_DEFAULT = "/opt/omnia/input/project_default/software_config.json"
SOFTWARE_CSV_FILENAME = "software.csv"
FRESH_INSTALLATION_STATUS = True

# ----------------------------
# Software Utilities Defaults
# Used by software_utils.py
# ----------------------------
PACKAGE_TYPES = ['rpm', 'deb', 'tarball', 'image', 'manifest', 'git',
                 'pip_module', 'deb', 'shell', 'ansible_galaxy_collection', 'iso', 'rpm_list']
CSV_COLUMNS = {"column1": "name", "column2": "status"}
SOFTWARE_CONFIG_SUBDIR = "config"
RPM_LABEL_TEMPLATE = "RPMs for {key}"
RHEL_OS_URL = "rhel_os_url"
SOFTWARES_KEY = "softwares"
USER_REPO_URL = "user_repo_url"
REPO_CONFIG = { "always": "on_demand", "partial": "on_demand", "never": "streamed" }
ARCH_SUFFIXES = {"x86_64", "aarch64"}
DNF_COMMANDS = {
    "x86_64": ["dnf", "download", "--resolve", "--alldeps", "--arch=x86_64,noarch"],
    "aarch64": ["dnf", "download", "--forcearch", "aarch64", "--resolve", "--alldeps", "--exclude=*.x86_64"]
}

# ----------------------------
# Used by download_common.py
# ----------------------------
# Pulp command templates
pulp_file_commands = {
    "create_repository": "pulp file repository create --name %s",
    "show_repository": "pulp file repository show --name %s",
    "download_content": "wget -c -O %s %s",
    "content_upload": "pulp file content upload --repository %s --file %s --relative-path %s",
    "publication_create": "pulp file publication create --repository %s",
    "show_distribution": "pulp file distribution show --name %s",
    "distribution_create": "pulp file distribution create --name %s --base-path %s --repository %s",
    "distribution_update": "pulp file distribution update --name %s --base-path %s --repository %s",
}
CLI_FILE_PATH = "/root/.config/pulp/cli.toml"
POST_TIMEOUT = 3600
TAR_POLL_VAL = 3
FILE_POLL_VAL = 1
ISO_POLL_VAL = 15
FILE_URI = "/pulp/api/v3/content/file/files/"
PULP_SSL_CA_CERT = "/etc/pki/ca-trust/source/anchors/pulp_webserver.crt"
# ----------------------------
# Used by download_image.py
# ----------------------------

pulp_container_commands = {
    "create_container_repo": "pulp container repository create --name %s",
    "show_container_repo": "pulp container repository show --name %s",
    "create_container_remote": "pulp container remote create --name %s --url %s --upstream-name %s --policy %s --include-tags '[\"%s\"]'",
    "create_container_remote_for_digest": "pulp container remote create --name %s --url %s --upstream-name %s --policy %s",
    "create_user_remote_tag": "pulp container remote create --name %s --url %s --upstream-name %s --policy %s --include-tags '[\"%s\"]' --ca-cert %s --client-key %s --tls-validation false",
    "update_user_remote_tag": "pulp container remote update --name %s --url %s --upstream-name %s --policy %s --include-tags '%s' --ca-cert %s --client-key %s --tls-validation false",
    "update_user_remote_digest": "pulp container remote update --name %s --url %s --upstream-name %s --policy %s  --ca-cert %s --client-key %s --tls-validation false",
    "create_user_remote_digest": "pulp container remote create --name %s --url %s --upstream-name %s --policy %s --ca-cert %s --client-key %s --tls-validation false",
    "update_remote_for_digest": "pulp container remote update --name %s --url %s --upstream-name %s --policy %s",
    "update_container_remote": "pulp container remote update --name %s --url %s --upstream-name %s --policy %s --include-tags '%s'",
    "show_container_remote": "pulp container remote show --name %s",
    "show_container_distribution": "pulp container distribution show --name %s",
    "sync_container_repository": "pulp container repository sync --name %s --remote %s",
    "distribute_container_repository": "pulp container distribution create --name %s --repository %s --base-path %s",
    "update_container_distribution": "pulp container distribution update --name %s --repository %s --base-path %s",
    "list_container_remote_tags": "pulp container remote list --name %s --field include_tags",

    "create_container_remote_auth": "pulp container remote create --name %s --url %s --upstream-name %s --policy %s --include-tags '%s' --username %s --password '%s'",

    "update_container_remote_auth": "pulp container remote update --name %s --url %s --upstream-name %s --policy %s --include-tags '%s' --username %s --password '%s'",
    "container_distribution_show": "pulp container distribution show --name %s | jq .repository",
    "show_repository_version": "pulp container repository show --href %s | jq .latest_version_href",
    "list_image_tags": "pulp show --href /pulp/api/v3/content/container/tags/?repository_version=%s"
}
OMNIA_CREDENTIALS_YAML_PATH = "/opt/omnia/input/project_default/omnia_config_credentials.yml"
OMNIA_CREDENTIALS_VAULT_PATH = "/opt/omnia/input/project_default/.omnia_config_credentials_key"
# ----------------------------
# Used by process_rpm_config.py
# ----------------------------

# Pulp Concurrency Settings
# Controls the number of concurrent sync/publish operations
PULP_CONCURRENCY = 1  # Default: 1 (most reliable for NFS)

pulp_rpm_commands = {
    "create_repository": "pulp rpm repository create --name %s",
    "pulp_cleanup": "pulp orphan cleanup",
    "show_repository": "pulp rpm repository show --name %s",
    "create_remote": "pulp rpm remote create --name %s --url %s --policy %s",
    "show_remote": "pulp rpm remote show --name %s",
    "update_remote": "pulp rpm remote update --name %s --url %s --policy %s",
    "sync_repository": "pulp rpm repository sync --name %s --remote %s",
    "publish_repository": "pulp rpm publication create --repository %s",
    "distribute_repository": "pulp rpm distribution create --name %s  --base-path %s  --repository %s",
    "update_distribution": "pulp rpm distribution update --name %s  --base-path %s  --repository %s",
    "create_remote_cert": "pulp rpm remote create --name %s --url %s --policy %s --ca-cert %s --client-cert %s --client-key %s",
    "update_remote_cert": "pulp rpm remote update --name %s --url %s --policy %s --ca-cert %s --client-cert %s --client-key %s",
    "check_distribution": "pulp rpm distribution show --name %s",
    "delete_repository": "pulp rpm repository destroy --name %s",
    "delete_remote": "pulp rpm remote destroy --name %s",
    "delete_distribution": "pulp rpm distribution destroy --name %s",
    "list_publications": "pulp rpm publication list --repository %s",
    "update_distribution_publication": "pulp rpm distribution update --name %s --publication %s",
    "check_distribution": "pulp rpm distribution show --name %s",
    "check_publication": "pulp rpm publication list --repository %s",
    "delete_publication": "pulp rpm publication destroy --href %s",
    "get_repo_version": "pulp rpm repository show --name %s"
}

# ----------------------------
# Additional Repos Aggregation Settings
# Used by process_rpm_config.py for aggregated repos feature
# Naming convention: <arch>_omnia-additional to match existing filter patterns
# ----------------------------
ADDITIONAL_REPOS_KEY = "additional_repos"
AGGREGATED_REPO_NAME_TEMPLATE = "{arch}_omnia-additional-repo"
AGGREGATED_REMOTE_NAME_TEMPLATE = "{arch}_omnia-additional-{name}"
AGGREGATED_DISTRIBUTION_NAME_TEMPLATE = "{arch}_omnia-additional"
AGGREGATED_BASE_PATH_TEMPLATE = "opt/omnia/offline_repo/cluster/{arch}/rhel/10.0/rpms/omnia-additional"
STANDARD_LOG_FILE_PATH = "/opt/omnia/log/local_repo/standard.log"

# ----------------------------
# Used by cert_vault_handle.py
# ----------------------------
CERT_KEYS = ["sslcacert", "sslclientkey", "sslclientcert"]

# ----------------------------
# Used by process_metadata.py
# ----------------------------
metadata_rerun_file_path = "/opt/omnia/offline_repo/.data/localrepo_rerun_metadata.yml"
