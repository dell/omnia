"""Shared constants for Config Editor module."""

# Bundle classification constants
# Single source of truth for bundle categorization across services
FUNCTIONAL_BUNDLES = frozenset({"service_k8s", "slurm_custom", "additional_packages"})
INFRA_BUNDLES = frozenset({"csi_driver_powerscale"})
OS_BUNDLES = frozenset({
    "default_packages", "admin_debug_packages",
    "openldap", "openmpi", "ucx", "ldms", "nfs",
})
ALL_KNOWN_BUNDLES = FUNCTIONAL_BUNDLES | INFRA_BUNDLES | OS_BUNDLES
