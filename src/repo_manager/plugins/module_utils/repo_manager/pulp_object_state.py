# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Tri-state reads for Pulp objects.

Only an explicit not-found diagnostic is absence. Authentication, transport,
JSON, and execution failures are unknown and never authorize object creation
or replacement.
"""


_NOT_FOUND_MARKERS = (
    "404",
    "could not find",
    "does not exist",
    "matches the given query",
    "no object found with name",
    "no result found",
)


def query_pulp_object(command, logger, executor):
    """Return ``(present, data)``; ``present`` is True, False, or None."""
    result = executor(
        command,
        logger,
        type_json=True,
        enhanced_error_info=True,
    )
    if not isinstance(result, dict):
        return None, None
    if result.get("success", result.get("returncode") == 0):
        output = result.get("stdout")
        if isinstance(output, (dict, list)):
            return True, output
        return None, None

    diagnostic = " ".join(
        str(result.get(field) or "") for field in ("stdout", "stderr")
    ).casefold()
    if any(marker in diagnostic for marker in _NOT_FOUND_MARKERS):
        return False, None
    return None, None
