# NFS Client Role

## Overview
Configures NFS client mounts on cluster nodes based on their functional roles.

## Purpose
- Filters and mounts NFS shares based on node type (Slurm, Kubernetes)
- Configures NFS client packages
- Creates mount points and persistent `/etc/fstab` entries
- Supports bolt-on storage additions

## Key Tasks
- **Load Configuration**: Reads storage and software configuration
- **Filter Slurm Mounts**: Identifies NFS shares required for Slurm nodes
- **Filter K8s Mounts**: Identifies NFS shares required for Kubernetes service nodes
- **Install NFS Client**: Installs packages, creates mount points, updates `/etc/fstab`, mounts shares

