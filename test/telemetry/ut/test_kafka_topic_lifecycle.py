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

"""Contract tests for non-destructive Kafka topic lifecycle reconciliation."""

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
KAFKA_TASKS = REPO_ROOT / "src/telemetry/roles/deploy_kafka/tasks"


def _tasks(name):
    return yaml.safe_load((KAFKA_TASKS / name).read_text(encoding="utf-8"))


def _task_by_name(tasks, name):
    return next(task for task in tasks if task.get("name") == name)


def test_disabled_sources_remove_only_stale_topic_manifests():
    """Disabling a source removes its local YAML without deleting Kafka data."""
    prepare = _tasks("prepare.yml")
    remove = _task_by_name(
        prepare, "Remove Kafka topic manifests for disabled sources"
    )

    assert remove["ansible.builtin.file"]["state"] == "absent"
    assert remove["loop"] == ["idrac", "ldms"]
    assert "metrics_enabled" in remove["when"]
    assert "kubectl" not in str(remove).lower()
    assert "kafkatopic" not in str(remove).lower()
    assert "pvc" not in str(remove).lower()


def test_topic_deployment_never_discovers_stale_manifests_by_wildcard():
    """Only configured source names may reach the Kafka topic apply command."""
    deploy = _tasks("deploy.yml")
    topic_block = _task_by_name(
        deploy, "Apply source-specific Kafka topics"
    )["block"]
    apply = _task_by_name(
        topic_block, "Apply Kafka topic manifests for enabled sources"
    )

    assert apply["loop"] == ["idrac", "ldms"]
    assert any("metrics_enabled" in condition for condition in apply["when"])
    assert "ansible.builtin.find" not in str(topic_block)
    assert "kafka.*.topic.yaml" not in str(topic_block)


def test_topic_readiness_wait_is_limited_to_enabled_sources():
    """Readiness checks use the same source gate as topic application."""
    deploy = _tasks("deploy.yml")
    topic_block = _task_by_name(
        deploy, "Apply source-specific Kafka topics"
    )["block"]
    wait = _task_by_name(
        topic_block, "Wait for enabled Kafka topics to be ready"
    )

    assert wait["loop"] == ["idrac", "ldms"]
    assert any("metrics_enabled" in condition for condition in wait["when"])
    argv = wait["ansible.builtin.command"]["argv"]
    assert any("kafka.{{ item }}.topic.yaml" in argument for argument in argv)
