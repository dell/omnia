# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Contract tests for independent, non-destructive OME reconciliation."""

from pathlib import Path

import pytest
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

REPO_ROOT = Path(__file__).resolve().parents[3]
OME_ROLE = REPO_ROOT / "src/telemetry/roles/deploy_ome"
DEPLOY_PLAYBOOK = REPO_ROOT / "src/telemetry/playbooks/deploy/deploy.yml"
DEPLOY_SINKS_PLAYBOOK = (
    REPO_ROOT / "src/telemetry/playbooks/deploy/sinks/deploy_sinks.yml"
)
TELEMETRY_PREREQ = (
    REPO_ROOT / "src/telemetry/playbooks/deploy/telemetry_prereq.yml"
)
OME_PLAYBOOK = (
    REPO_ROOT / "src/telemetry/playbooks/deploy/sources/deploy_ome.yml"
)


def _read(path):
    return path.read_text(encoding="utf-8")


def _tasks(name):
    return yaml.safe_load(_read(OME_ROLE / "tasks" / name))


def _task_by_name(tasks, name):
    return next(task for task in tasks if task.get("name") == name)


def _render_vector_config(metrics_enabled, logs_enabled):
    environment = Environment(
        loader=FileSystemLoader(str(OME_ROLE / "templates")),
        undefined=StrictUndefined,
        autoescape=False,
    )
    environment.filters["bool"] = bool
    template = environment.get_template("vector-ome-config.toml.j2")
    return template.render(
        telemetry_namespace="telemetry",
        telemetry_config={
            "telemetry_bridges": {
                "vector_ome": {
                    "metrics_enabled": metrics_enabled,
                    "logs_enabled": logs_enabled,
                    "ome_identifier": "ome",
                },
            },
        },
        vector={
            "ome": {
                "consumer_group": "vector-ome-group",
                "kafka_topics_pattern": r"^ome\\..*$",
                "metrics_port": 9598,
            },
            "vmagent_vector": {"service_name": "vmagent-vector", "port": 8429},
            "vlagent_vector": {"service_name": "vlagent-vector", "port": 9427},
        },
    )


def test_full_deploy_always_invokes_ome_reconciliation():
    """False bridge flags must not skip the OME disable path."""
    plays = yaml.safe_load(_read(DEPLOY_PLAYBOOK))
    ome = next(
        play for play in plays
        if play.get("name") == "Phase 2 | Deploy OME telemetry"
    )

    assert ome["ansible.builtin.import_playbook"].endswith("deploy_ome.yml")
    assert "when" not in ome


def test_full_deploy_allows_empty_derived_sinks_for_disable_reconciliation():
    """All-disabled reruns must reach source reconciliation without deploying sinks."""
    plays = yaml.safe_load(_read(DEPLOY_PLAYBOOK))
    sink_import = next(
        play for play in plays
        if play.get("name") == "Phase 1 | Deploy telemetry sinks"
    )
    assert sink_import["vars"]["allow_empty_sinks"] is True

    sink_plays = yaml.safe_load(_read(DEPLOY_SINKS_PLAYBOOK))
    validation = _task_by_name(
        sink_plays[0]["tasks"], "Ensure sinks is a valid list"
    )
    assertions = validation["ansible.builtin.assert"]["that"]
    assert any("allow_empty_sinks" in assertion for assertion in assertions)


def test_ome_dependency_validation_precedes_cluster_changes():
    """Full and standalone deploys validate source/bridge pairs before sinks."""
    prereq = yaml.safe_load(_read(TELEMETRY_PREREQ))[0]
    prereq_names = [task["name"] for task in prereq["tasks"]]

    validation_index = prereq_names.index(
        "Validate OME source-to-bridge dependencies"
    )
    assert validation_index < prereq_names.index("Derive sink support flags")

    play = yaml.safe_load(_read(OME_PLAYBOOK))[0]
    ordered_tasks = play["pre_tasks"] + play["tasks"]
    names = [task["name"] for task in ordered_tasks]

    validation_index = names.index("Validate OME source-to-bridge dependencies")
    assert validation_index < names.index(
        "Deploy Kafka (handles both cluster deployment and topic management)"
    )
    assert validation_index < names.index(
        "Deploy VictoriaMetrics/VictoriaLogs (standalone run only)"
    )

    validation = _read(OME_ROLE / "tasks/validate_dependencies.yml")
    assert "telemetry_sources.ome.metrics_enabled is false" in validation
    assert "telemetry_sources.ome.logs_enabled is false" in validation


@pytest.mark.parametrize(
    ("metrics_enabled", "logs_enabled"),
    [(True, True), (True, False), (False, True), (False, False)],
)
def test_all_ome_channel_combinations_render_expected_vector_routes(
        metrics_enabled, logs_enabled):
    """Each channel independently controls its transforms and sink."""
    rendered = _render_vector_config(metrics_enabled, logs_enabled)

    assert ("[transforms.metric_enricher]" in rendered) is metrics_enabled
    assert ("[sinks.victoria_metrics]" in rendered) is metrics_enabled
    assert ("[transforms.ome_log_enricher]" in rendered) is logs_enabled
    assert ("[sinks.victoria_logs]" in rendered) is logs_enabled
    assert ("[sinks.drop_unmatched]" in rendered) is (not metrics_enabled)


def test_ome_disable_is_idempotent_and_non_destructive():
    """Disable scales retained workloads and never deletes shared state."""
    disable = _tasks("disable.yml")
    discover = _task_by_name(disable, "Check if OME Vector resources exist")
    scale = _task_by_name(disable, "Scale down OME Vector resources")
    text = _read(OME_ROLE / "tasks/disable.yml").lower()

    assert "--ignore-not-found" in discover["ansible.builtin.command"]
    assert "--replicas=0" in scale["ansible.builtin.command"]
    assert "kubectl delete" not in text
    assert "persistentvolumeclaim" not in text
    assert "kafkauser" not in text
    assert "secret" not in text


def test_ome_restore_reconciles_configured_replicas_without_creation():
    """Re-enable explicitly restores scaled Deployments after apply."""
    restore = _read(OME_ROLE / "tasks/restore.yml")
    generate = _read(OME_ROLE / "tasks/generate_manifests.yml")

    assert "vector.ome.replicas | int" in restore
    assert "vector.vmagent_vector.replicas | int" in restore
    assert "vector.vlagent_vector.replicas | int" in restore
    assert "kubectl scale deployment" in restore
    assert "kubectl create" not in restore
    assert "kubectl delete" not in restore
    assert "kubectl apply -f" in generate


def test_ome_disabled_forwarders_protect_shared_ldms_vmagent():
    """OME metrics disable cannot stop vmagent while Vector-LDMS uses it."""
    reconcile = _read(OME_ROLE / "tasks/reconcile_disabled_channels.yml")

    assert "telemetry_config.telemetry_sources.ldms.metrics_enabled" in reconcile
    assert "telemetry_config.telemetry_bridges.vector_ldms.metrics_enabled" in reconcile
    assert "kubectl delete" not in reconcile


def test_ome_status_reports_each_channel_as_deployed_or_disabled():
    """A partial OME deployment reports independent channel outcomes."""
    deploy = _read(DEPLOY_PLAYBOOK)

    assert "_deploy_result_ome_metrics" in deploy
    assert "_deploy_result_ome_logs" in deploy
    assert "-l app=vmagent-vector" in deploy
    assert "-l app=vlagent-vector" in deploy
    assert "_ome_metrics_forwarder_running" in deploy
    assert "_ome_logs_forwarder_running" in deploy
    assert "'skipped' if not (_ome_m_on | bool)" in deploy
    assert "'skipped' if not (_ome_l_on | bool)" in deploy
