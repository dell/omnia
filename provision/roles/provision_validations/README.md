# Provision Validations Role

## Overview
Validates all node provision-related configuration files and inputs before the provision process begins.

## Purpose
- Validates provision input files syntax and structure
- Checks software configuration consistency
- Validates mapping files when mapping-based provision is used
- Ensures telemetry configuration is correct
- Updates system hosts file with provisioned nodes

## Key Tasks
- **Load Credentials**: Securely loads provisioning and BMC credentials
- **Validate Provision Inputs**: Checks syntax of provision configuration files
- **Validate Software Config**: Ensures software configuration is consistent
- **Validate Mapping File**: Validates node mapping file (MAC, IP, hostname uniqueness)
- **Update Hosts File**: Updates `/etc/hosts` with node information
- **Validate Telemetry**: Validates telemetry configuration when enabled
