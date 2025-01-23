#!/bin/bash

# Backup all resources
kubectl get all --all-namespaces -o yaml > all-resources.yaml

# Backup ConfigMaps and Secrets
kubectl get configmaps --all-namespaces -o yaml > configmaps.yaml
kubectl get secrets --all-namespaces -o yaml > secrets.yaml

# Backup Deployements
kubectl get deployments --all-namespaces -o yaml > deployments.yaml

# Backup PVCs
kubectl get pvc --all-namespaces -o yaml > pvcs.yaml

# Backup PVs
kubectl get pv  -A -o yaml > pv.yaml

# Backup CRDs
kubectl get crd -o yaml > crds.yaml

# Backup Cluster Roles and Role Bindings
kubectl get clusterroles -o yaml > clusterroles.yaml
kubectl get clusterrolebindings -o yaml > clusterrolebindings.yaml

# Backup Namespaces
kubectl get namespaces -o yaml > namespaces.yaml

# Backup Service Accounts
kubectl get serviceaccounts --all-namespaces -o yaml > serviceaccounts.yaml

# Backup Network Policies
kubectl get networkpolicies --all-namespaces -o yaml > networkpolicies.yaml

# Backup Resource Quotas and Limit Ranges
kubectl get resourcequotas --all-namespaces -o yaml > resourcequotas.yaml
kubectl get limitranges --all-namespaces -o yaml > limitranges.yaml

# Statefulsets
kubectl get statefulsets -A -o yaml > statefulsets.yaml

# Daemonsets
kubectl get daemonsets --all-namespaces -o yaml > all-daemonsets.yaml
echo "Backup completed successfully."
