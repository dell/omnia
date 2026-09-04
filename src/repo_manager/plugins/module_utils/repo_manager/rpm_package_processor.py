# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Policy decisions shared by Repo Manager RPM package processing."""


def catalog_rpm_type(package_name, rpm_type_mapping):
    """Return the supported catalog RPM type for a package."""
    package_type = rpm_type_mapping.get(package_name, "rpm")
    return package_type if package_type in ("rpm", "rpm_repo") else "rpm"


def partition_rpm_work(rpm_list, rpm_type_mapping, repo_config_value):
    """Split RPMs into payload downloads and metadata validations."""
    if repo_config_value == "always":
        return list(rpm_list), [], False

    downloads = [
        package_name for package_name in rpm_list
        if catalog_rpm_type(package_name, rpm_type_mapping) == "rpm_repo"
    ]
    validations = [
        package_name for package_name in rpm_list
        if package_name not in downloads
    ]
    return downloads, validations, True
