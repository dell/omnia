# K8s Config Role

## Overview
Creates Kubernetes configuration files for the service cluster and stores them in NFS-shared storage.

## Purpose
- Generates Kubernetes manifests for cluster services
- Creates Helm chart values files
- Prepares ConfigMaps and Secrets for deployments
- Stores configurations in NFS for service cluster access

## Key Tasks
- **Create Config Directory**: Creates NFS directory structure for K8s configurations
- **Generate Manifests**: Creates Namespaces, RBAC, ConfigMaps, Secrets, Services, Deployments
- **Create Helm Values**: Generates Helm chart values files for services
- **Set Permissions**: Sets appropriate file permissions and ownership
