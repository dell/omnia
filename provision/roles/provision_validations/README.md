# Discovery Validations Role

## Overview
Validates all node discovery-related configuration files and inputs before the discovery process begins.

## Purpose
- Validates discovery input files syntax and structure
- Checks software configuration consistency
- Validates mapping files when mapping-based discovery is used
- Ensures telemetry configuration is correct
- Updates system hosts file with discovered nodes

## Key Tasks
- **Load Credentials**: Securely loads provisioning and BMC credentials
- **Validate Discovery Inputs**: Checks syntax of discovery configuration files
- **Validate Software Config**: Ensures software configuration is consistent
- **Validate Mapping File**: Validates node mapping file (MAC, IP, hostname uniqueness)
- **Update Hosts File**: Updates `/etc/hosts` with node information
- **Validate Telemetry**: Validates telemetry configuration when enabled
