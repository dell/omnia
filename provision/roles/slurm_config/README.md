# Slurm Config Role

## Overview
Configures Slurm workload manager directory structures on NFS.

## Purpose
- Identifies Slurm nodes (control, compute, login)
- Creates shared Slurm directories on NFS
- Sets up directories for logs, spool files, and state information

## Key Tasks
- **Load Configuration**: Reads software configuration to check Slurm support
- **Identify Nodes**: Gets Slurm controller, compute, and login node hostnames
- **Create Directories**: Creates shared NFS directories for Slurm state, spool, and logs
