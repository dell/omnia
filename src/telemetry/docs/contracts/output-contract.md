# Telemetry — Output Contract

## Overview

The telemetry domain writes a status file after execution to communicate its
completion state to downstream domains and the `omnia-cli`.

## Output Files

### telemetry_status.yml

Written after telemetry deployment completes (or fails).

**Location**: 
- `<OMNIA_DATA_PATH>/telemetry/output/<project>/telemetry_status.yml`

| Key | Type | Description |
|-----|------|-------------|
| `domain` | string | Always `telemetry` |
| `project_name` | string | Active project name |
| `overall_status` | string | One of: `success`, `failed`, `partial`, `skipped` |
| `execution_time` | string | ISO 8601 timestamp of execution |
| `duration_seconds` | int | Total execution duration |
| `tags_executed` | list | Tags that were executed |
| `details` | dict | Per-component deployment status |
| `errors` | list | Error messages (empty on success) |

### Example

```yaml
domain: telemetry
project_name: project_default
overall_status: success
execution_time: "2026-08-04T12:00:00Z"
duration_seconds: 120
tags_executed:
  - deploy
details:
  victoria_metrics: deployed
  kafka: deployed
  ldms: deployed
  idrac: deployed
errors: []
```

## Downstream Consumers

No downstream domains currently depend on `telemetry_status.yml`. The status
file is consumed by:
- `omnia-cli check` — validates domain execution status
- Operators — manual verification of deployment state
