# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Pure helpers for building multi-context Repo Manager status output."""


def summarize_execution_contexts(execution_contexts):
    """Return the stable public fields for each catalog execution context."""
    return [
        {
            "context_id": context.get(
                "context_id",
                f"{context['os_type']}_{context['os_version']}",
            ),
            "os_type": context["os_type"],
            "os_version": str(context["os_version"]),
            "architectures": list(context["architectures"]),
        }
        for context in execution_contexts
    ]


def build_terminal_context_status(execution_contexts, execution_results=None,
                                  requested_status="success"):
    """Return final per-version and aggregate status for one invocation.

    Download execution supplies ``execution_results``. Contexts not reached
    after a failure remain pending, while the aggregate remains failed. The
    standalone status operation omits results and derives readiness directly
    from the live Pulp inspection represented by ``requested_status``.
    """
    normalized_requested = str(requested_status).lower()
    results = execution_results or []
    result_by_context = {
        result.get("context_id"): str(result.get("status", "failed")).lower()
        for result in results
        if isinstance(result, dict) and result.get("context_id")
    }
    status_by_version = {}
    for context in execution_contexts:
        context_id = context.get(
            "context_id",
            f"{context['os_type']}_{context['os_version']}",
        )
        if results:
            context_status = result_by_context.get(context_id, "pending")
        else:
            context_status = normalized_requested
        if context_status not in ("success", "failed", "pending"):
            context_status = "failed"
        status_by_version[str(context["os_version"])] = context_status

    selected_statuses = list(status_by_version.values())
    if normalized_requested == "failed":
        aggregate_status = "failed"
    elif selected_statuses and all(
            status == "success" for status in selected_statuses):
        aggregate_status = "success"
    elif any(status == "failed" for status in selected_statuses):
        aggregate_status = "failed"
    else:
        aggregate_status = "in_progress"
    return status_by_version, aggregate_status


def merge_context_status(previous_status, execution_contexts,
                         active_os_version, active_status):
    """Merge one context result and return per-version and aggregate status."""
    selected_versions = [
        str(context["os_version"]) for context in execution_contexts
    ]
    previous_values = (
        (previous_status or {}).get("overall_status_by_version") or {}
    )
    status_by_version = {
        str(version): status
        for version, status in previous_values.items()
        if str(version) in selected_versions
    }
    active_os_version = str(active_os_version)
    if selected_versions and active_os_version == selected_versions[0]:
        # The first deterministic context starts a new status-generation pass.
        # Ignore successful selected-version values left by an earlier run.
        for version in selected_versions:
            status_by_version[version] = "pending"
    status_by_version[active_os_version] = str(active_status).lower()
    selected_statuses = [
        status_by_version.get(version, "pending")
        for version in selected_versions
    ]
    if selected_statuses and all(
            status == "success" for status in selected_statuses):
        aggregate_status = "success"
    elif any(status == "failed" for status in selected_statuses):
        aggregate_status = "failed"
    else:
        aggregate_status = "in_progress"
    return status_by_version, aggregate_status


def merge_version_mapping(previous_status, field_name, active_os_version,
                          active_value, selected_versions=None):
    """Replace one version while retaining only selected catalog versions."""
    values = dict((previous_status or {}).get(field_name) or {})
    if selected_versions is not None:
        selected = {str(version) for version in selected_versions}
        values = {
            str(version): value
            for version, value in values.items()
            if str(version) in selected
        }
    values[str(active_os_version)] = active_value
    return values
