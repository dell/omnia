# Configure OpenCHAMI Role

## Overview
Configures OpenCHAMI (Open Composable Heterogeneous Adaptable Management
Infrastructure) for node lifecycle management in HPC clusters.

## Purpose
- Creates and manages SMD (State Management Database) groups for node organization
- Configures OpenCHAMI Boot Service boot parameters
- Publishes cloud-init data through OpenCHAMI Metadata Service
- Manages node metadata and grouping by functional roles

## Key Tasks
- **Create Groups**: Generates OpenCHAMI group definitions from mapping files
- **Configure Boot Service**: Sets boot parameters for node orchestration
- **Configure Metadata Service**: Publishes cluster, group, and node metadata
  used to render cloud-init for node initialization
- **Orchestration Completion**: Finalizes the orchestration process
