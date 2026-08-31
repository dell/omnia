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
# pylint: disable=line-too-long

"""
Pulp CLI command templates and DNF command definitions.
"""

pulp_file_commands = {
    "create_repository": "pulp file repository create --name %s",
    "show_repository": "pulp file repository show --name %s",
    "download_content": "wget -c -O %s %s",
    "content_upload": "pulp file content upload --repository %s --file %s --relative-path %s",
    "publication_create": "pulp file publication create --repository %s",
    "show_distribution": "pulp file distribution show --name %s",
    "distribution_create": "pulp file distribution create --name %s --base-path %s --repository %s",
    "distribution_update": "pulp file distribution update --name %s --base-path %s --repository %s",

    # Cleanup commands
    "delete_repository": "pulp file repository destroy --name %s",
    "delete_distribution": "pulp file distribution destroy --name %s",
    "delete_publication": "pulp file publication destroy --href %s",
    "list_publications": "pulp file publication list --repository %s --limit 1000",
    "list_repositories": "pulp file repository list --limit 1000",
    "list_distributions": "pulp file distribution list --limit 1000",
    "list_content": "pulp file content list --repository-version %s --limit 1000",
    "show_repository_version": "pulp file repository version show --repository %s",
    "orphan_cleanup": "pulp orphan cleanup --protection-time 0"
}

pulp_python_commands = {
    "list_repositories": "pulp python repository list --limit 1000",
    "show_repository": "pulp python repository show --name %s",
    "delete_repository": "pulp python repository destroy --name %s",
    "list_distributions": "pulp python distribution list --limit 1000",
    "delete_distribution": "pulp python distribution destroy --name %s",
    "list_publications": "pulp python publication list --repository %s --limit 1000",
    "delete_publication": "pulp python publication destroy --href %s",
    "orphan_cleanup": "pulp orphan cleanup --protection-time 0"
}

pulp_container_commands = {
    "create_container_repo": "pulp container repository create --name %s",
    "show_container_repo": "pulp container repository show --name %s",
    "container_distribution_show": "pulp container distribution show --name %s",
    "show_repository_version": "pulp container repository version show --repository-href %s",
    "list_image_tags": "pulp show --href '/pulp/api/v3/content/container/tags/?repository_version=%s'",
    "create_container_remote": "pulp container remote create --name %s --url %s --upstream-name %s --policy %s --include-tags '[\"%s\"]' --exclude-tags '[\"*sha256*.sig\"]'",
    "create_container_remote_for_digest": "pulp container remote create --name %s --url %s --upstream-name %s --policy %s --exclude-tags '[\"*sha256*.sig\"]'",
    "update_remote_for_digest": "pulp container remote update --name %s --url %s --upstream-name %s --policy %s --exclude-tags '[\"*sha256*.sig\"]'",
    "update_container_remote": "pulp container remote update --name %s --url %s --upstream-name %s --policy %s --include-tags '%s' --exclude-tags '[\"*sha256*.sig\"]'",
    "show_container_remote": "pulp container remote show --name %s",
    "show_container_distribution": "pulp container distribution show --name %s",
    "sync_container_repository": "pulp container repository sync --name %s --remote %s",
    "distribute_container_repository": "pulp container distribution create --name %s --repository %s --base-path %s",
    "update_container_distribution": "pulp container distribution update --name %s --repository %s --base-path %s",
    "list_container_remote_tags": "pulp container remote list --name %s --field includes",
    # Cleanup commands. These names and options are supported by pulp-cli
    # 0.40.5 and match the objects created by download_image.py.
    "list_repositories": "pulp container repository list --limit 1000",
    "delete_repository": "pulp container repository destroy --name %s",
    "list_distributions": "pulp container distribution list --limit 1000",
    "delete_distribution": "pulp container distribution destroy --name %s",
    "list_remotes": "pulp container remote list --limit 1000",
    "delete_remote": "pulp container remote destroy --name %s",
    "create_container_remote_auth": "pulp container remote create --name %s --url %s --upstream-name %s --policy %s --include-tags '%s' --exclude-tags '[\"*sha256*.sig\"]' --username %s --password '%s'",
    "update_container_remote_auth": "pulp container remote update --name %s --url %s --upstream-name %s --policy %s --include-tags '%s' --exclude-tags '[\"*sha256*.sig\"]' --username %s --password '%s'",
    "create_container_remote_for_digest_auth": "pulp container remote create --name %s --url %s --upstream-name %s --policy %s --exclude-tags '[\"*sha256*.sig\"]' --username %s --password '%s'",
    "update_remote_for_digest_auth": "pulp container remote update --name %s --url %s --upstream-name %s --policy %s --exclude-tags '[\"*sha256*.sig\"]' --username %s --password '%s'"
}

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
    "list_publications": "pulp rpm publication list --repository %s --limit 1000",
    "update_distribution_publication": "pulp rpm distribution update --name %s --publication %s",
    "check_publication": "pulp rpm publication list --repository %s --limit 1000",
    "delete_publication": "pulp rpm publication destroy --href %s",
    "get_repo_version": "pulp rpm repository show --name %s",
    "list_repositories": "pulp rpm repository list --limit 1000",
    "list_remotes": "pulp rpm remote list --limit 1000",
    "list_distributions": "pulp rpm distribution list --limit 1000",
    "orphan_cleanup": "pulp orphan cleanup --protection-time 0",
    "list_all_publications": "pulp rpm publication list --limit 1000",
    "upload_content": "pulp rpm content upload --repository %s --file %s",
    "update_distribution_repo_config": "pulp rpm distribution update --name %s --generate-repo-config"
}

DNF_COMMANDS = {
    "x86_64": ["dnf", "download", "--refresh", "--resolve", "--alldeps", "--arch=x86_64", "--arch=noarch", "--disablerepo=*", "--enablerepo=x86_64_*"],
    "aarch64": ["dnf", "download", "--refresh", "--forcearch", "aarch64", "--resolve", "--alldeps", "--exclude=*.x86_64", "--disablerepo=*", "--enablerepo=aarch64_*"]
}

DNF_INFO_COMMANDS = {
    "x86_64": ["dnf", "info", "--refresh", "--quiet"],
    "aarch64": ["dnf", "info", "--refresh", "--quiet", "--forcearch=aarch64"]
}

__all__ = [
    "pulp_file_commands",
    "pulp_python_commands",
    "pulp_container_commands",
    "pulp_rpm_commands",
    "DNF_COMMANDS",
    "DNF_INFO_COMMANDS",
]
