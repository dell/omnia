"""
Data schemas and type definitions for Config Editor Module

Provides data models and validation schemas for configuration files.
These correspond to the actual configuration file structures used by OMNIA.

Note: Catalog-related types have been moved to catalog_schemas.py (Pydantic)
to avoid duplication and maintain a single source of truth.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class SchedulerType(Enum):
    """Scheduler type for cluster configuration"""
    KUBERNETES = "kubernetes"
    SLURM = "slurm"
    BOTH = "both"

@dataclass
class Package:
    """Package definition"""
    name: str
    type: str  # Using str instead of PackageType enum to avoid circular imports
    version: Optional[str] = None
    uri: Optional[str] = None
    tag: Optional[str] = None
    repo_name: Optional[str] = None
    architecture: List[str] = field(default_factory=list)


@dataclass
class Bundle:
    """Software bundle configuration"""
    name: str
    architecture: List[str]
    packages: List[Package] = field(default_factory=list)


@dataclass
class SoftwareConfig:
    """Software configuration from software_config.json"""
    cluster_os_type: str = "rhel"
    cluster_os_version: str = "10.0"
    repo_config: str = "partial"
    softwares: List[Dict[str, Any]] = field(default_factory=list)
    slurm_custom: List[Dict[str, str]] = field(default_factory=list)
    service_k8s: List[Dict[str, str]] = field(default_factory=list)
    additional_packages: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class PXEFunctionalGroup:
    """PXE functional group mapping"""
    functional_group_name: str
    group_name: str
    service_tag: Optional[str] = None
    parent_service_tag: Optional[str] = None
    hostname: Optional[str] = None
    admin_mac: Optional[str] = None
    admin_ip: Optional[str] = None
    bmc_mac: Optional[str] = None
    bmc_ip: Optional[str] = None
    ib_nic_name: Optional[str] = None
    ib_ip: Optional[str] = None


@dataclass
class DeploymentConfig:
    """Deployment configuration (storage, security, omnia)"""
    provision_config: Optional[Dict[str, Any]] = None
    network_spec: Optional[Dict[str, Any]] = None
    storage_config: Optional[Dict[str, Any]] = None
    security_config: Optional[Dict[str, Any]] = None
    omnia_config: Optional[Dict[str, Any]] = None


@dataclass
class FeatureConfig:
    """Feature-specific configuration (optional)"""
    telemetry_config: Optional[Dict[str, Any]] = None
    telemetry_storage_config: Optional[Dict[str, Any]] = None
    high_availability_config: Optional[Dict[str, Any]] = None
    discovery_config: Optional[Dict[str, Any]] = None
    gitlab_config: Optional[Dict[str, Any]] = None
    local_repo_config: Optional[Dict[str, Any]] = None
    build_stream_config: Optional[Dict[str, Any]] = None
    user_registry_credential: Optional[Dict[str, Any]] = None


@dataclass
class Configuration:
    """Complete configuration state"""
    software_config: SoftwareConfig = field(default_factory=SoftwareConfig)
    bundles: Dict[str, Bundle] = field(default_factory=dict)
    pxe_functional_groups: List[PXEFunctionalGroup] = field(default_factory=list)
    deployment_config: DeploymentConfig = field(default_factory=DeploymentConfig)
    feature_config: FeatureConfig = field(default_factory=FeatureConfig)
