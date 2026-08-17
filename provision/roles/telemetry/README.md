# Telemetry Role

## Overview
Configures telemetry services for HPC cluster monitoring, including iDRAC telemetry streaming and LDMS (Lightweight Distributed Metric Service).

## Purpose
- Collects hardware metrics from Dell iDRAC interfaces
- Deploys LDMS agents for system-level metrics collection
- Sets up data aggregation and storage infrastructure
- Configures Kafka for telemetry data streaming
- Deploys time-series databases for metric storage

## Key Tasks
- **Load Configuration**: Reads telemetry configuration and software config
- **Setup Prerequisites**: Creates Kubernetes namespace and RBAC resources
- **Generate Deployments**: Creates deployment manifests for telemetry services
- **Configure LDMS**: Sets up LDMS samplers and aggregators
- **Configure iDRAC**: Sets up iDRAC telemetry streamers
- **Validate Inventory**: Validates iDRAC connectivity and endpoints

## Telemetry Components
- **iDRAC Telemetry**: Collects hardware metrics (temperature, power, fan speeds) from iDRAC
- **LDMS**: Collects OS-level metrics (CPU, memory, network, disk) from compute nodes
- **Kafka**: Streams telemetry data
- **Time-Series Database**: Stores metrics (VictoriaMetrics)
