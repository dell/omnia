"""Helper functions for telemetry sink/source logic.
Routing topology:

Each telemetry source has ``metrics_enabled`` / ``logs_enabled`` boolean
flags and a ``collection_targets`` list (e.g. ``["kafka"]``,
``["victoria_metrics"]``, ``["victoria_logs"]``).

Direct paths
    source (metrics_enabled=True) -> victoria_metrics
    source (logs_enabled=True)    -> victoria_logs

Kafka bridge paths
    LDMS (metrics) -> Kafka -> Vector-LDMS -> victoria_metrics
    OME  (metrics) -> Kafka -> Vector-OME  -> victoria_metrics
    OME  (logs)    -> Kafka -> Vector-OME  -> victoria_logs

LDMS does not produce logs, so no LDMS bridge path exists for logs.
"""

from typing import Any, Dict, FrozenSet, Iterator, List, Tuple


# Current assumption: all Kafka bridge paths terminate at a Victoria sink.
# If Kafka is used for non-Victoria consumers in the future, this logic
# will need an explicit bridge-destination config field.

_TARGET_KAFKA = "kafka"
_TARGET_VICTORIA_METRICS = "victoria_metrics"
_TARGET_VICTORIA_LOGS = "victoria_logs"
_SINK_VECTOR = "vector"

# Sources that route to Victoria* through Vector when Kafka is a target.
_METRICS_BRIDGE_SOURCES = frozenset({"ldms", "ome"})
_LOGS_BRIDGE_SOURCES = frozenset({"ome"})


def _active_sources(
    telemetry_sources: Dict[str, Any], capability: str = "metrics_enabled"
) -> Iterator[Tuple[str, Dict[str, Any], List[str]]]:
    """Yield (name, config, targets) for sources with ``capability`` enabled.

    ``collection_targets`` is defensively normalized to a list; non-list
    values are ignored to avoid substring false-positives such as
    ``"kafka" in "kafka_cluster"``.
    """
    if not isinstance(telemetry_sources, dict):
        return
    for name, cfg in telemetry_sources.items():
        if not isinstance(cfg, dict):
            continue
        if not cfg.get(capability, False):
            continue
        collection_targets = cfg.get("collection_targets", [])
        if not isinstance(collection_targets, list):
            continue
        yield name, cfg, collection_targets


def required_sinks(telemetry_sources: Dict[str, Any]) -> FrozenSet[str]:
    """Return the set of infrastructure sinks required by the telemetry sources.

    The returned strings are:
        - "victoria_metrics"
        - "victoria_logs"
        - "kafka"
        - "vector"
    """
    sinks = set()

    for name, _, targets in _active_sources(telemetry_sources, "metrics_enabled"):
        if _TARGET_VICTORIA_METRICS in targets:
            sinks.add(_TARGET_VICTORIA_METRICS)
        if _TARGET_KAFKA in targets:
            sinks.add(_TARGET_KAFKA)
            if name in _METRICS_BRIDGE_SOURCES:
                sinks.update({_TARGET_VICTORIA_METRICS, _SINK_VECTOR})

    for name, _, targets in _active_sources(telemetry_sources, "logs_enabled"):
        if _TARGET_VICTORIA_LOGS in targets:
            sinks.add(_TARGET_VICTORIA_LOGS)
        if _TARGET_KAFKA in targets:
            sinks.add(_TARGET_KAFKA)
            if name in _LOGS_BRIDGE_SOURCES:
                sinks.update({_TARGET_VICTORIA_LOGS, _SINK_VECTOR})

    return frozenset(sinks)


def needs_victoria_metrics(telemetry_sources: Dict[str, Any]) -> bool:
    """Check if victoria_metrics sink is needed based on collection targets.

    Only ``metrics_enabled`` sources are considered.
    """
    return _TARGET_VICTORIA_METRICS in required_sinks(telemetry_sources)


def needs_victoria_logs(telemetry_sources: Dict[str, Any]) -> bool:
    """Check if victoria_logs sink is needed based on collection targets.

    Only ``logs_enabled`` sources are considered.
    """
    return _TARGET_VICTORIA_LOGS in required_sinks(telemetry_sources)


def needs_kafka(telemetry_sources: Dict[str, Any]) -> bool:
    """Check if Kafka sink is needed based on collection targets.

    A source is considered active when either ``metrics_enabled`` or
    ``logs_enabled`` is True; Kafka is needed if any active source lists
    ``"kafka"`` in its targets.
    """
    return _TARGET_KAFKA in required_sinks(telemetry_sources)


def needs_vector(telemetry_sources: Dict[str, Any]) -> bool:
    """Check if Vector is needed for LDMS or OME bridges via Kafka.

    Vector is needed when LDMS metrics or OME metrics/logs are routed to
    Kafka, which is then bridged to the Victoria* sinks.
    """
    return _SINK_VECTOR in required_sinks(telemetry_sources)
