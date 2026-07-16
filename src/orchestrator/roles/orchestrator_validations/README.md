# Orchestrator Validations Role

## Overview
Validates all node orchestration-related configuration files and inputs before the orchestration process begins.

## Purpose
- Validates orchestrator input files syntax and structure
- Checks software configuration consistency
- Validates mapping files when mapping-based orchestration is used
- Ensures telemetry configuration is correct
- Updates system hosts file with orchestrated nodes

## Key Tasks
- **Load Credentials**: Securely loads orchestration and BMC credentials
- **Validate Orchestrator Inputs**: Checks syntax of orchestrator configuration files
- **Validate Software Config**: Ensures software configuration is consistent
- **Validate Mapping File**: Validates node mapping file (MAC, IP, hostname uniqueness)
- **Update Hosts File**: Updates `/etc/hosts` with node information
- **Validate Telemetry**: Validates telemetry configuration when enabled
