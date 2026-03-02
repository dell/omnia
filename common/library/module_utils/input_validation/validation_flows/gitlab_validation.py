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
# pylint: disable=import-error,no-name-in-module,too-many-positional-arguments,too-many-arguments,unused-argument
"""
Validates gitlab_config.yml input for hosted GitLab deployment.
"""
import ipaddress
import re
from ansible.module_utils.input_validation.common_utils import validation_utils
from ansible.module_utils.input_validation.common_utils import config
from ansible.module_utils.input_validation.common_utils import en_us_validation_msg as msg

file_names = config.files
create_error_msg = validation_utils.create_error_msg
create_file_path = validation_utils.create_file_path

VALID_BRANCH_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._\-/]*$')
VALID_VISIBILITY_VALUES = ["private", "internal", "public"]


def validate_gitlab_config(input_file_path, data,
                            logger, module, omnia_base_dir,
                            module_utils_base, project_name):
    """
    Validates gitlab_config.yml by performing logical checks on all user-configurable
    fields including gitlab_host, project settings, port numbers, resource thresholds,
    and OIM API configuration.

    Args:
        input_file_path (str): Path to the input file directory.
        data (dict): Loaded YAML data from gitlab_config.yml.
        logger (Logger): Logger instance.
        module (AnsibleModule): Ansible module instance.
        omnia_base_dir (str): Base directory of Omnia.
        module_utils_base (str): Base directory of module_utils.
        project_name (str): Name of the project.

    Returns:
        list: A list of error dicts encountered during validation.
    """
    errors = []
    gitlab_yml = create_file_path(input_file_path, file_names["gitlab_config"])

    _validate_gitlab_host(data, gitlab_yml, errors, logger)
    _validate_project_settings(data, gitlab_yml, errors)
    _validate_ports(data, gitlab_yml, errors)
    _validate_resource_requirements(data, gitlab_yml, errors)
    _validate_performance_tuning(data, gitlab_yml, errors)
    _validate_oim_settings(data, gitlab_yml, errors)

    return errors


def _validate_gitlab_host(data, gitlab_yml, errors, logger):
    """Validate gitlab_host is a non-empty valid IPv4 address."""
    gitlab_host = data.get("gitlab_host", "")

    if not gitlab_host or not gitlab_host.strip():
        errors.append(create_error_msg(gitlab_yml, "gitlab_host",
                                       msg.GITLAB_HOST_EMPTY_MSG))
        return

    try:
        ipaddress.IPv4Address(gitlab_host.strip())
    except ValueError:
        errors.append(create_error_msg(gitlab_yml, "gitlab_host",
                                       msg.GITLAB_HOST_INVALID_IP_MSG))
        return

    logger.info("gitlab_host validated: %s", gitlab_host)


def _validate_project_settings(data, gitlab_yml, errors):
    """Validate gitlab_project_name, gitlab_project_visibility, and gitlab_default_branch."""
    project_name = data.get("gitlab_project_name", "")
    if not project_name or not str(project_name).strip():
        errors.append(create_error_msg(gitlab_yml, "gitlab_project_name",
                                       msg.GITLAB_PROJECT_NAME_EMPTY_MSG))

    visibility = data.get("gitlab_project_visibility", "")
    if visibility not in VALID_VISIBILITY_VALUES:
        errors.append(create_error_msg(gitlab_yml, "gitlab_project_visibility",
                                       msg.GITLAB_PROJECT_VISIBILITY_INVALID_MSG))

    branch = data.get("gitlab_default_branch", "")
    if not branch or not str(branch).strip():
        errors.append(create_error_msg(gitlab_yml, "gitlab_default_branch",
                                       msg.GITLAB_DEFAULT_BRANCH_EMPTY_MSG))
    elif not VALID_BRANCH_PATTERN.match(str(branch)):
        errors.append(create_error_msg(gitlab_yml, "gitlab_default_branch",
                                       msg.GITLAB_DEFAULT_BRANCH_INVALID_MSG))


def _validate_ports(data, gitlab_yml, errors):
    """Validate gitlab_https_port and gitlab_ssh_port are valid port numbers."""
    https_port = data.get("gitlab_https_port")
    if https_port is not None:
        if not isinstance(https_port, int) or not 1 <= https_port <= 65535:
            errors.append(create_error_msg(gitlab_yml, "gitlab_https_port",
                                           msg.GITLAB_HTTPS_PORT_INVALID_MSG))

    ssh_port = data.get("gitlab_ssh_port")
    if ssh_port is not None:
        if not isinstance(ssh_port, int) or not 1 <= ssh_port <= 65535:
            errors.append(create_error_msg(gitlab_yml, "gitlab_ssh_port",
                                           msg.GITLAB_SSH_PORT_INVALID_MSG))

    if (https_port is not None and ssh_port is not None
            and isinstance(https_port, int) and isinstance(ssh_port, int)
            and https_port == ssh_port):
        errors.append(create_error_msg(gitlab_yml, "gitlab_https_port",
                                       msg.GITLAB_PORTS_CONFLICT_MSG))


def _validate_resource_requirements(data, gitlab_yml, errors):
    """Validate minimum storage, memory, and CPU requirements."""
    min_storage = data.get("gitlab_min_storage_gb")
    if min_storage is not None:
        if not isinstance(min_storage, int) or min_storage < 10:
            errors.append(create_error_msg(gitlab_yml, "gitlab_min_storage_gb",
                                           msg.GITLAB_MIN_STORAGE_INVALID_MSG))

    min_memory = data.get("gitlab_min_memory_gb")
    if min_memory is not None:
        if not isinstance(min_memory, int) or min_memory < 1:
            errors.append(create_error_msg(gitlab_yml, "gitlab_min_memory_gb",
                                           msg.GITLAB_MIN_MEMORY_INVALID_MSG))

    min_cpu = data.get("gitlab_min_cpu_cores")
    if min_cpu is not None:
        if not isinstance(min_cpu, int) or min_cpu < 1:
            errors.append(create_error_msg(gitlab_yml, "gitlab_min_cpu_cores",
                                           msg.GITLAB_MIN_CPU_INVALID_MSG))


def _validate_performance_tuning(data, gitlab_yml, errors):
    """Validate puma workers and sidekiq concurrency values."""
    puma_workers = data.get("gitlab_puma_workers")
    if puma_workers is not None:
        if not isinstance(puma_workers, int) or not 1 <= puma_workers <= 64:
            errors.append(create_error_msg(gitlab_yml, "gitlab_puma_workers",
                                           msg.GITLAB_PUMA_WORKERS_INVALID_MSG))

    sidekiq_concurrency = data.get("gitlab_sidekiq_concurrency")
    if sidekiq_concurrency is not None:
        if not isinstance(sidekiq_concurrency, int) or not 1 <= sidekiq_concurrency <= 200:
            errors.append(create_error_msg(gitlab_yml, "gitlab_sidekiq_concurrency",
                                           msg.GITLAB_SIDEKIQ_CONCURRENCY_INVALID_MSG))


def _validate_oim_settings(data, gitlab_yml, errors):
    """Validate oim_api_verify_ssl is a boolean."""
    oim_verify_ssl = data.get("oim_api_verify_ssl")
    if oim_verify_ssl is not None and not isinstance(oim_verify_ssl, bool):
        errors.append(create_error_msg(gitlab_yml, "oim_api_verify_ssl",
                                       msg.GITLAB_OIM_VERIFY_SSL_INVALID_MSG))
