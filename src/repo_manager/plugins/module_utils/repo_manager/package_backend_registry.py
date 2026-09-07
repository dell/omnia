# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Registered Pulp package backends for enabled Repo Manager platforms."""


_IMPLEMENTED_BACKENDS = {
    "pulp_rpm": {
        "package_types": ("rpm", "rpm_list", "rpm_file", "rpm_repo"),
        "ansible_module": "process_rpm_config",
    },
}


def get_package_backend(backend_name):
    """Return an implemented backend descriptor or raise a clear error."""
    backend = _IMPLEMENTED_BACKENDS.get(str(backend_name or ""))
    if backend is None:
        raise ValueError(
            f"Package backend '{backend_name}' is not implemented or enabled"
        )
    return dict(backend)
