# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=missing-function-docstring,too-many-branches,too-many-locals
"""Idempotent OpenCHAMI reconciliation operations used by Ansible."""

import json
import re
from collections.abc import Iterable
from typing import Any

from .client import BootServiceClient, MetadataClient, OpenChamiClient, SMDClient
from .discovery import StaticDiscovery
from .identity import SMDIdentityResolver, normalize_mac


class OpenChamiReconciler:
    """Coordinate identity, SMD, and Metadata Service operations."""

    MANAGED_BY_LABEL = "omnia.dell.com/managed-by"
    PROJECT_LABEL = "omnia.dell.com/project"
    # Group metaData keys that hold one entry per host. They grow with the node
    # list, so a change that only adds or edits host entries concerns those
    # hosts and must not make every other node of the cluster reprovision.
    INVENTORY_METADATA_KEYS = ("host_mount_map",)
    # The same for generated text: the host list a template writes into
    # /etc/hosts sits between these comment lines, which are valid in a hosts
    # file. A change that is confined to such a region concerns the hosts
    # whose line was added or edited.
    INVENTORY_REGION = re.compile(
        r"^[ \t]*# omnia-inventory-begin[ \t]*\n(?P<body>.*?)"
        r"^[ \t]*# omnia-inventory-end[ \t]*$",
        re.DOTALL | re.MULTILINE,
    )
    MANAGED_BY_VALUE = "omnia"

    def __init__(self, base_url, token, ca_cert=None, timeout=15, retries=3):
        client = OpenChamiClient(
            base_url=base_url,
            token=token,
            ca_cert=ca_cert,
            timeout=timeout,
            retries=retries,
        )
        self.smd = SMDClient(client)
        self.metadata = MetadataClient(client)
        self.boot = BootServiceClient(client)
        self.client = client

    def check_apis(self):
        """Validate TLS, JWT authentication, and the required read APIs."""
        checks = {}
        endpoints = {
            "smd_health": ("/hsm/v2/service/ready", dict),
            "smd_components": ("/hsm/v2/State/Components", (dict, list)),
            "smd_interfaces": (
                "/hsm/v2/Inventory/EthernetInterfaces",
                list,
            ),
            "smd_hardware_inventory": (
                "/hsm/v2/Inventory/Hardware",
                list,
            ),
            "smd_groups": ("/hsm/v2/groups", list),
            "metadata_health": ("/metadata-service/health", dict),
            "metadata_instanceinfos": (
                "/metadata-service/instanceinfos",
                list,
            ),
            "metadata_groups": ("/metadata-service/groups", list),
            "metadata_cluster_defaults": (
                "/metadata-service/clusterdefaultss",
                list,
            ),
            "boot_health": ("/boot-service/health", dict),
            "boot_configurations": (
                "/boot-service/bootconfigurations",
                list,
            ),
            "boot_nodes": ("/boot-service/nodes", list),
            "tokensmith_jwks": ("/tokensmith/.well-known/jwks.json", dict),
        }
        for name, (path, expected_type) in endpoints.items():
            response = self.client.request_json("GET", path)
            if not isinstance(response.body, expected_type):
                raise TypeError(
                    f"{path} returned unexpected payload type "
                    f"{type(response.body).__name__}"
                )
            checks[name] = {"status": response.status, "path": path}
        return {"changed": False, "checks": checks}

    def list_boot_configurations(self):
        """Return the Boot Service configurations through the verified client."""
        return {
            "changed": False,
            "boot_configurations": self.boot.boot_configurations(),
        }

    def reconcile_boot_configurations(
        self,
        desired: Iterable[dict[str, Any]],
        check_mode=False,
    ):
        """Create or replace Boot Service configurations by metadata name."""
        existing_by_name = {}
        for resource in self.boot.boot_configurations():
            name = str(resource.get("metadata", {}).get("name", "")).strip()
            if name:
                existing_by_name.setdefault(name, []).append(resource)

        created = []
        updated = []
        unchanged = []
        deleted_duplicate_uids = []
        seen = set()

        for item in desired:
            name, desired_spec = self._desired_resource(
                item, "Boot Service configuration"
            )
            if name in seen:
                raise ValueError(
                    f"Duplicate desired Boot Service configuration {name!r}"
                )
            seen.add(name)
            matches = existing_by_name.get(name, [])
            matching = [
                resource
                for resource in matches
                if self._boot_spec(resource.get("spec") or {})
                == self._boot_spec(desired_spec)
            ]

            if matching:
                canonical = sorted(
                    matching,
                    key=lambda resource: str(
                        resource.get("metadata", {}).get("uid", "")
                    ),
                )[0]
                self._resource_uid(
                    canonical, "Boot Service configuration", name
                )
                duplicate_resources = [
                    resource for resource in matches if resource is not canonical
                ]
                for duplicate in duplicate_resources:
                    uid = self._resource_uid(
                        duplicate, "Boot Service configuration", name
                    )
                    if not check_mode:
                        self.boot.delete_boot_configuration(uid)
                    deleted_duplicate_uids.append(uid)
                unchanged.append(name)
                continue

            for current in matches:
                uid = self._resource_uid(
                    current, "Boot Service configuration", name
                )
                if not check_mode:
                    self.boot.delete_boot_configuration(uid)

            payload = {
                "metadata": {"name": name},
                "spec": desired_spec,
            }
            if not check_mode:
                self.boot.create_boot_configuration(payload)
            (updated if matches else created).append(name)

        if not check_mode:
            self._verify_boot_configurations(desired)
        return {
            "changed": bool(created or updated or deleted_duplicate_uids),
            "created": created,
            "updated": updated,
            "unchanged": unchanged,
            "deleted_duplicate_uids": deleted_duplicate_uids,
        }

    def prune_boot_configurations(
        self,
        desired_names: Iterable[str],
        target_macs: Iterable[str],
        check_mode=False,
    ):
        """Delete stale non-target boot configurations that claim target MACs."""
        desired = set(self._unique(desired_names))
        managed_macs = {normalize_mac(value) for value in target_macs if value}
        deleted = []

        for resource in self.boot.boot_configurations():
            metadata = resource.get("metadata") or {}
            name = str(metadata.get("name", "")).strip()
            if not name or name in desired:
                continue
            spec = resource.get("spec") or {}
            resource_macs = {
                normalize_mac(value) for value in (spec.get("macs") or [])
            }
            if not managed_macs.intersection(resource_macs):
                continue
            uid = self._resource_uid(
                resource, "Boot Service configuration", name
            )
            if not check_mode:
                self.boot.delete_boot_configuration(uid)
            deleted.append({"name": name, "uid": uid})

        return {"changed": bool(deleted), "deleted": deleted}

    def resolve_identities(
        self,
        nodes,
        check_mode=False,
    ):
        """Resolve XNAMEs from native SMD Service Tag FRU records."""
        return SMDIdentityResolver(self.smd).resolve_nodes(
            nodes=nodes,
            check_mode=check_mode,
        )

    def reconcile_groups(self, desired: Iterable[dict[str, Any]], check_mode=False):
        """Create missing SMD groups and atomically reconcile their members."""
        existing_by_label = {}
        for group in self.smd.groups():
            label = str(group.get("label", "")).strip()
            if not label:
                continue
            if label in existing_by_label:
                raise ValueError(f"SMD returned duplicate group label {label!r}")
            existing_by_label[label] = group

        created = []
        updated = []
        unchanged = []
        seen = set()
        for requested in desired:
            if not isinstance(requested, dict):
                raise TypeError("Each desired SMD group must be a mapping")
            label = str(requested.get("label", "")).strip()
            if not label:
                raise ValueError("Each desired SMD group requires a label")
            if label in seen:
                raise ValueError(f"Duplicate desired SMD group {label!r}")
            seen.add(label)
            members_block = requested.get("members") or {}
            if not isinstance(members_block, dict):
                raise TypeError(
                    f"Desired SMD group {label!r} members must be a mapping"
                )
            requested_members = members_block.get("ids", [])
            if not isinstance(requested_members, list):
                raise TypeError(
                    f"Desired SMD group {label!r} members.ids must be a list"
                )
            members = self._unique(requested_members)
            if len(members) != len(requested_members):
                raise ValueError(
                    f"Desired SMD group {label!r} contains duplicate members"
                )

            current = existing_by_label.get(label)
            if current is None:
                payload = dict(requested)
                payload["label"] = label
                payload["members"] = {"ids": members}
                if not check_mode:
                    self.smd.create_group(payload)
                created.append(label)
                continue

            current_members = self._unique(
                (current.get("members") or {}).get("ids", [])
            )
            if set(current_members) == set(members):
                unchanged.append(label)
                continue
            if not check_mode:
                self.smd.set_group_members(label, members)
            updated.append(label)

        return {
            "changed": bool(created or updated),
            "created": created,
            "updated": updated,
            "unchanged": unchanged,
        }

    def remove_group_memberships(
        self,
        target_xnames: Iterable[str],
        protected_labels: Iterable[str],
        check_mode=False,
    ):
        """Remove target nodes from every non-protected SMD group."""
        targets = set(self._unique(target_xnames))
        protected = set(self._unique(protected_labels))
        removals = []
        for group in self.smd.groups():
            label = str(group.get("label", "")).strip()
            if not label or label in protected:
                continue
            members = (group.get("members") or {}).get("ids", []) or []
            for xname in sorted(targets.intersection(members)):
                removals.append({"label": label, "xname": xname})

        if not check_mode:
            for removal in removals:
                self.smd.delete_group_member(
                    removal["label"], removal["xname"]
                )
        return {"changed": bool(removals), "removed": removals}

    def delete_groups(self, labels: Iterable[str], check_mode=False):
        """Delete explicitly named SMD groups without failing on absence."""
        requested = self._unique(labels)
        existing = {
            str(group.get("label", "")).strip()
            for group in self.smd.groups()
            if group.get("label")
        }
        present = [label for label in requested if label in existing]
        if not check_mode:
            for label in present:
                self.smd.delete_group(label)
        return {
            "changed": bool(present),
            "deleted": present,
            "missing": [label for label in requested if label not in existing],
        }

    def cleanup_smd(
        self,
        component_endpoint_xnames: Iterable[str],
        redfish_endpoint_xnames: Iterable[str],
        interface_macs: Iterable[str],
        check_mode=False,
    ):
        """Delete category-scoped discovery artifacts, treating absence as success."""
        component_targets = self._unique(component_endpoint_xnames)
        interface_targets = {
            normalize_mac(value) for value in interface_macs if value
        }
        # Delete every interface owned by a target Node/NodeBMC before static
        # discovery. This removes an old MAC after a NIC or BMC replacement;
        # deleting only the new PXE MAC would leave the stale record behind.
        for interface in self.smd.interfaces():
            if str(interface.get("ComponentID", "")).strip() not in component_targets:
                continue
            identifier = interface.get("ID") or interface.get("MACAddress")
            if identifier:
                interface_targets.add(normalize_mac(identifier))

        targets = {
            "component_endpoints": component_targets,
            "redfish_endpoints": self._unique(redfish_endpoint_xnames),
            "interfaces": sorted(interface_targets),
        }
        if check_mode:
            return {
                "changed": any(targets.values()),
                "planned": targets,
                "results": {},
            }
        results = {
            "component_endpoints": self.smd.delete_component_endpoints(
                targets["component_endpoints"]
            ),
            "redfish_endpoints": self.smd.delete_redfish_endpoints(
                targets["redfish_endpoints"]
            ),
            "interfaces": self.smd.delete_interfaces(targets["interfaces"]),
        }
        changed = any(value["deleted"] for value in results.values())
        return {"changed": changed, "planned": targets, "results": results}

    def cleanup_orphan_smd_entries(
        self,
        current_service_tags: Iterable[str],
        current_macs: Iterable[str],
        check_mode=False,
    ):
        """Remove SMD entries for nodes no longer in the PXE mapping.

        Compares the current PXE mapping service tags and MACs against SMD
        Hardware Inventory, EthernetInterfaces, Components, and Groups.
        Any XNAME whose service tag is not in the current mapping — and
        whose MACs are not in the current mapping — is treated as an orphan
        from a previous deployment and is fully cleaned up:

          1. Remove the orphan XNAME from every SMD group
          2. Delete its EthernetInterfaces (admin NIC + BMC)
          3. Delete its Components (Node + NodeBMC)
          4. Delete its Hardware Inventory record

        This runs once before per-category provisioning so that
        ``resolve_identities`` and ``prune_metadata_groups`` never encounter
        stale entries from replaced physical servers.
        """
        from .identity import normalize_mac as _norm_mac, normalize_service_tag

        active_tags = {
            normalize_service_tag(tag) for tag in current_service_tags if tag
        }
        active_macs = {_norm_mac(mac) for mac in current_macs if mac}

        # --- Identify orphan XNAMEs from Hardware Inventory ---
        hardware = self.smd.hardware_inventory()
        interfaces = self.smd.interfaces()
        active_interface_xnames = set()
        for interface in interfaces:
            mac_raw = interface.get("MACAddress") or interface.get("ID")
            if not mac_raw:
                continue
            try:
                mac = _norm_mac(mac_raw)
            except Exception:
                continue
            if mac not in active_macs:
                continue
            component_id = str(interface.get("ComponentID", "")).strip()
            iface_type = str(interface.get("Type", "")).lower()
            if iface_type == "node" and component_id:
                active_interface_xnames.add(component_id)
            elif iface_type == "nodebmc" and component_id:
                active_interface_xnames.add(component_id + "n0")

        orphan_xnames = set()
        for record in hardware:
            if str(record.get("Type", "")).lower() != "node":
                continue
            xname = str(record.get("ID", "")).strip()
            if not xname:
                continue
            tag_value = (
                record.get("PopulatedFRU", {})
                .get("NodeFRUInfo", {})
                .get("SerialNumber", "")
            )
            if not tag_value:
                continue
            try:
                tag = normalize_service_tag(tag_value)
            except Exception:
                continue
            if tag not in active_tags and xname not in active_interface_xnames:
                orphan_xnames.add(xname)

        # --- Also find component XNAMEs with interfaces whose MACs are not
        #     in the current mapping AND have no hardware inventory (nodes
        #     that were discovered but never got an inventory record) ---
        hardware_xnames = {
            str(r.get("ID", "")).strip()
            for r in hardware
            if str(r.get("Type", "")).lower() == "node" and r.get("ID")
        }
        for interface in interfaces:
            component_id = str(interface.get("ComponentID", "")).strip()
            if not component_id:
                continue
            mac_raw = interface.get("MACAddress") or interface.get("ID")
            if not mac_raw:
                continue
            try:
                mac = _norm_mac(mac_raw)
            except Exception:
                continue
            # If MAC belongs to current mapping, this interface is live
            if mac in active_macs:
                continue
            # Derive node xname from interface component
            iface_type = str(interface.get("Type", "")).lower()
            if iface_type == "node":
                node_xname = component_id
            elif iface_type == "nodebmc":
                node_xname = component_id + "n0"
            else:
                continue
            # Only add if this node has no hardware record (already covered)
            # or is already in orphan_xnames
            if node_xname not in hardware_xnames:
                orphan_xnames.add(node_xname)

        if not orphan_xnames:
            return {
                "changed": False,
                "orphan_xnames": [],
                "group_removals": [],
                "deleted_interfaces": [],
                "deleted_components": [],
                "deleted_hardware": [],
            }

        if check_mode:
            return {
                "changed": True,
                "orphan_xnames": sorted(orphan_xnames),
                "group_removals": [],
                "deleted_interfaces": [],
                "deleted_components": [],
                "deleted_hardware": [],
            }

        # 1. Remove orphan XNAMEs from ALL SMD groups
        group_removals = []
        for group in self.smd.groups():
            label = str(group.get("label", "")).strip()
            if not label:
                continue
            members = set((group.get("members") or {}).get("ids", []) or [])
            orphans_in_group = orphan_xnames.intersection(members)
            for xname in sorted(orphans_in_group):
                self.smd.delete_group_member(label, xname)
                group_removals.append({"label": label, "xname": xname})

        # 2. Delete orphan interfaces (both node NIC and BMC NIC)
        orphan_bmc_xnames = {
            ox[:-2] for ox in orphan_xnames if ox.endswith("n0")
        }
        orphan_interface_ids = set()
        for interface in interfaces:
            component_id = str(interface.get("ComponentID", "")).strip()
            if (
                component_id in orphan_xnames
                or component_id in orphan_bmc_xnames
            ):
                iface_id = interface.get("ID") or interface.get("MACAddress")
                if iface_id:
                    orphan_interface_ids.add(_norm_mac(iface_id))

        iface_result = self.smd.delete_interfaces(sorted(orphan_interface_ids))

        # 3. Delete orphan components (Node + NodeBMC)
        orphan_components = sorted(orphan_xnames | orphan_bmc_xnames)
        comp_result = self.smd.delete_components(orphan_components)

        # Also delete component endpoints and redfish endpoints
        self.smd.delete_component_endpoints(orphan_components)
        self.smd.delete_redfish_endpoints(sorted(orphan_bmc_xnames))

        # 4. Delete orphan hardware inventory
        hw_result = self.smd.delete_hardware_inventory(sorted(orphan_xnames))

        return {
            "changed": True,
            "orphan_xnames": sorted(orphan_xnames),
            "group_removals": group_removals,
            "deleted_interfaces": iface_result.get("deleted", []),
            "deleted_components": comp_result.get("deleted", []),
            "deleted_hardware": hw_result.get("deleted", []),
        }

    def discover_static(
        self,
        nodes_file,
        access_token,
        token_env_key,
        expected_xnames,
        check_mode=False,
    ):
        """Run static discovery and verify all requested components exist."""
        expected = set(self._unique(expected_xnames))
        if check_mode:
            return {"changed": True, "planned_xnames": sorted(expected)}
        result = StaticDiscovery().run(
            nodes_file,
            access_token,
            token_env_key,
            self.client.base_url,
            self.client.ca_cert,
        )
        verification = self.verify_components(expected)
        result.update({"changed": True, "verification": verification})
        return result

    def verify_components(self, expected_xnames: Iterable[str]):
        expected = set(self._unique(expected_xnames))
        actual = {
            component.get("ID")
            for component in self.smd.components()
            if component.get("Type") == "Node"
        }
        missing = sorted(expected - actual)
        if missing:
            raise ValueError(
                "SMD registration verification failed; missing node XNAMEs: "
                + ", ".join(missing)
            )
        return {"expected": sorted(expected), "missing": []}

    def reconcile_metadata_groups(
        self,
        desired: Iterable[dict[str, Any]],
        project_name: str,
        check_mode=False,
    ):
        """Create or update Omnia-owned Metadata Service groups by name."""
        ownership = self._ownership_labels(project_name)
        existing_by_name = self._resources_by_name(
            self.metadata.groups(), "Metadata Service group"
        )
        created = []
        updated = []
        inventory_updated = {}
        adopted = []
        unchanged = []
        seen = set()

        for item in desired:
            name, desired_spec = self._desired_resource(item, "group")
            if name in seen:
                raise ValueError(f"Duplicate desired Metadata Service group {name!r}")
            seen.add(name)
            current = existing_by_name.get(name)
            payload = {
                "metadata": {"name": name, "labels": ownership},
                "spec": desired_spec,
            }
            if current is None:
                if not check_mode:
                    self.metadata.create_group(payload)
                created.append(name)
                continue

            uid = self._resource_uid(current, "Metadata Service group", name)
            spec_changed = self._group_spec(current.get("spec") or {}) != self._group_spec(
                desired_spec
            )
            labels_changed = not self._has_ownership(current, ownership)
            if spec_changed or labels_changed:
                if not check_mode:
                    self.metadata.update_group(uid, payload)
                if not spec_changed:
                    adopted.append(name)
                    continue
                hosts = self._inventory_only_hosts(
                    current.get("spec") or {}, desired_spec
                )
                if hosts is None:
                    updated.append(name)
                else:
                    inventory_updated[name] = hosts
            else:
                unchanged.append(name)

        if not check_mode:
            self._verify_metadata_groups(desired, ownership)
        return {
            "changed": bool(created or updated or inventory_updated or adopted),
            "created": created,
            "updated": updated,
            "inventory_updated": inventory_updated,
            "adopted": adopted,
            "unchanged": unchanged,
        }

    def prune_metadata_groups(
        self,
        desired_names: Iterable[str],
        project_name: str,
        legacy_managed_names: Iterable[str],
        legacy_managed_prefixes: Iterable[str],
        check_mode=False,
    ):
        """Delete only stale Omnia-owned metadata groups with no SMD members."""
        desired = set(self._unique(desired_names))
        legacy_names = set(self._unique(legacy_managed_names))
        legacy_prefixes = tuple(self._unique(legacy_managed_prefixes))
        ownership = self._ownership_labels(project_name)
        smd_members = {
            str(group.get("label", "")).strip(): set(
                (group.get("members") or {}).get("ids", []) or []
            )
            for group in self.smd.groups()
            if group.get("label")
        }
        deleted = []
        delete_candidates = []
        retained = []
        blocked = []

        for group in self.metadata.groups():
            name = str(group.get("metadata", {}).get("name", "")).strip()
            if not name or name in desired:
                continue
            owned = self._has_ownership(group, ownership)
            legacy_owned = name in legacy_names or (
                bool(legacy_prefixes) and name.startswith(legacy_prefixes)
            )
            if not owned and not legacy_owned:
                retained.append(name)
                continue
            members = sorted(smd_members.get(name, set()))
            if members:
                blocked.append({"name": name, "members": members})
                continue
            uid = self._resource_uid(group, "Metadata Service group", name)
            delete_candidates.append((name, uid))

        if blocked:
            details = "; ".join(
                f"{item['name']}: {', '.join(item['members'])}" for item in blocked
            )
            raise ValueError(
                "Refusing to delete stale Metadata Service groups that still "
                f"have SMD members: {details}"
            )
        for name, uid in delete_candidates:
            if not check_mode:
                self.metadata.delete_group(uid)
            deleted.append(name)
        return {
            "changed": bool(deleted),
            "deleted": deleted,
            "retained_unmanaged": retained,
            "blocked": blocked,
        }

    def reconcile_cluster_defaults(
        self,
        desired: dict[str, Any],
        project_name: str,
        check_mode=False,
    ):
        """Reconcile the project-owned Metadata Service ClusterDefaults."""
        ownership = self._ownership_labels(project_name)
        name, desired_spec = self._desired_resource(desired, "ClusterDefaults")
        matches = [
            resource
            for resource in self.metadata.cluster_defaults()
            if str(resource.get("metadata", {}).get("name", "")).strip() == name
        ]
        matches.sort(
            key=lambda resource: self._canonical_resource_key(resource, ownership)
        )
        current = matches[0] if matches else None
        payload = {
            "metadata": {"name": name, "labels": ownership},
            "spec": desired_spec,
        }
        result = {
            "changed": False,
            "created": [],
            "updated": [],
            "adopted": [],
            "unchanged": [],
            "deleted_duplicate_uids": [],
        }
        if current is None:
            if not check_mode:
                created_resource = self.metadata.create_cluster_defaults(payload)
                created_uid = str(
                    (created_resource or {}).get("metadata", {}).get("uid", "")
                ).strip()
                self._verify_cluster_defaults(
                    name, desired_spec, ownership, expected_uid=created_uid or None
                )
            result["changed"] = True
            result["created"].append(name)
            return result

        uid = self._resource_uid(current, "Metadata Service ClusterDefaults", name)
        spec_changed = self._cluster_defaults_spec(
            current.get("spec") or {}
        ) != self._cluster_defaults_spec(desired_spec)
        labels_changed = not self._has_ownership(current, ownership)
        if spec_changed or labels_changed:
            if not check_mode:
                self.metadata.update_cluster_defaults(uid, payload)
            result["changed"] = True
            result["updated" if spec_changed else "adopted"].append(name)
        else:
            result["unchanged"].append(name)

        if not check_mode:
            self._verify_cluster_defaults(
                name, desired_spec, ownership, expected_uid=uid
            )
        for duplicate in matches[1:]:
            duplicate_uid = self._resource_uid(
                duplicate, "Metadata Service ClusterDefaults", name
            )
            if not check_mode:
                self.metadata.delete_cluster_defaults(duplicate_uid)
            result["deleted_duplicate_uids"].append(duplicate_uid)
        if result["deleted_duplicate_uids"]:
            result["changed"] = True
        return result

    def reconcile_instance_infos(
        self,
        desired: Iterable[dict[str, Any]],
        project_name: str,
        check_mode=False,
    ):
        """Create/update one InstanceInfo per XNAME and remove duplicates."""
        ownership = self._ownership_labels(project_name)
        existing = self.metadata.instance_infos()
        by_instance_id = {}
        for resource in existing:
            instance_id = str(resource.get("spec", {}).get("instance_id", "")).strip()
            if instance_id:
                by_instance_id.setdefault(instance_id, []).append(resource)

        created = []
        updated = []
        adopted = []
        deleted_duplicates = []
        unchanged = []
        seen = set()
        for item in desired:
            instance_id = str(item.get("instance_id", item.get("id", ""))).strip()
            hostname = str(item.get("hostname", "")).strip()
            if not instance_id or not hostname:
                raise ValueError("Each InstanceInfo requires instance_id and hostname")
            if instance_id in seen:
                raise ValueError(f"Duplicate desired InstanceInfo for {instance_id}")
            seen.add(instance_id)
            matches = sorted(
                by_instance_id.get(instance_id, []),
                key=lambda resource: str(
                    resource.get("metadata", {}).get("updatedAt", "")
                ),
                reverse=True,
            )
            desired_spec = {
                "instance_id": instance_id,
                "hostname": hostname,
                "local_hostname": hostname,
            }
            if not matches:
                if not check_mode:
                    self.metadata.create_instance_info(
                        {
                            "metadata": {"name": instance_id, "labels": ownership},
                            "spec": desired_spec,
                        }
                    )
                created.append(instance_id)
                continue

            canonical = matches[0]
            canonical_uid = canonical.get("metadata", {}).get("uid")
            if not canonical_uid:
                raise ValueError(f"InstanceInfo for {instance_id} has no metadata.uid")
            current_spec = dict(canonical.get("spec", {}))
            merged_spec = dict(current_spec)
            merged_spec.update(desired_spec)
            current_name = canonical.get("metadata", {}).get("name", "")
            spec_changed = current_spec != merged_spec or current_name != instance_id
            labels_changed = not self._has_ownership(canonical, ownership)
            if spec_changed or labels_changed:
                if not check_mode:
                    self.metadata.update_instance_info(
                        canonical_uid,
                        {
                            "metadata": {"name": instance_id, "labels": ownership},
                            "spec": merged_spec,
                        },
                    )
                (updated if spec_changed else adopted).append(instance_id)
            else:
                unchanged.append(instance_id)

            for duplicate in matches[1:]:
                duplicate_uid = duplicate.get("metadata", {}).get("uid")
                if not duplicate_uid:
                    raise ValueError(
                        f"Duplicate InstanceInfo for {instance_id} has no metadata.uid"
                    )
                if not check_mode:
                    self.metadata.delete_instance_info(duplicate_uid)
                deleted_duplicates.append(duplicate_uid)

        return {
            "changed": bool(created or updated or adopted or deleted_duplicates),
            "created": created,
            "updated": updated,
            "adopted": adopted,
            "unchanged": unchanged,
            "deleted_duplicate_uids": deleted_duplicates,
        }

    @classmethod
    def _ownership_labels(cls, project_name: str) -> dict[str, str]:
        project = str(project_name or "").strip()
        if not project:
            raise ValueError("project_name is required for metadata reconciliation")
        return {
            cls.MANAGED_BY_LABEL: cls.MANAGED_BY_VALUE,
            cls.PROJECT_LABEL: project,
        }

    @staticmethod
    def _has_ownership(resource, expected_labels) -> bool:
        labels = resource.get("metadata", {}).get("labels", {}) or {}
        return all(labels.get(key) == value for key, value in expected_labels.items())

    @staticmethod
    def _resources_by_name(resources, resource_type):
        indexed = {}
        for resource in resources:
            name = str(resource.get("metadata", {}).get("name", "")).strip()
            if not name:
                continue
            if name in indexed:
                raise ValueError(f"{resource_type} returned duplicate name {name!r}")
            indexed[name] = resource
        return indexed

    @staticmethod
    def _desired_resource(item, resource_type):
        if not isinstance(item, dict):
            raise TypeError(f"Desired {resource_type} must be a mapping")
        name = str(item.get("metadata", {}).get("name", "")).strip()
        spec = item.get("spec")
        if not name or not isinstance(spec, dict):
            raise ValueError(f"Desired {resource_type} requires metadata.name and spec")
        return name, dict(spec)

    @staticmethod
    def _resource_uid(resource, resource_type, name):
        uid = str(resource.get("metadata", {}).get("uid", "")).strip()
        if not uid:
            raise ValueError(f"{resource_type} {name!r} has no metadata.uid")
        return uid

    @classmethod
    def _canonical_resource_key(cls, resource, ownership):
        """Prefer an owned resource, then the oldest resource, then its UID."""
        metadata = resource.get("metadata", {}) or {}
        return (
            not cls._has_ownership(resource, ownership),
            str(metadata.get("createdAt", "")),
            str(metadata.get("uid", "")),
        )

    @classmethod
    def _inventory_only_hosts(cls, current_spec, desired_spec):
        """Return the hosts whose entries changed when only per-host data differs.

        The per-host maps in INVENTORY_METADATA_KEYS hold one entry per host.
        When the groups differ in nothing else, the result is the sorted list
        of hosts whose entry was added or edited (empty when entries were only
        removed); those are the only nodes the change concerns. Returns None
        when anything else differs or a map cannot be read, which keeps the
        group-wide handling.
        """
        current = cls._group_spec(current_spec)
        desired = cls._group_spec(desired_spec)
        hosts = set()
        for key in cls.INVENTORY_METADATA_KEYS:
            before = cls._host_entries(current["metaData"].pop(key, None))
            after = cls._host_entries(desired["metaData"].pop(key, None))
            if before is None or after is None:
                return None
            hosts.update(host for host, entry in after.items() if before.get(host) != entry)
        current["template"], before_regions = cls._split_regions(current["template"])
        desired["template"], after_regions = cls._split_regions(desired["template"])
        if len(before_regions) != len(after_regions):
            return None
        for before_body, after_body in zip(before_regions, after_regions):
            before_lines = cls._region_entries(before_body)
            after_lines = cls._region_entries(after_body)
            hosts.update(
                name for name, line in after_lines.items() if before_lines.get(name) != line
            )
        if current != desired:
            return None
        return sorted(hosts)

    @classmethod
    def _split_regions(cls, text):
        """Return the text with every inventory region masked, and the region bodies."""
        bodies = []

        def _mask(match):
            bodies.append(match.group("body"))
            return "# omnia-inventory-region"

        return cls.INVENTORY_REGION.sub(_mask, str(text)), bodies

    @staticmethod
    def _region_entries(body):
        """Return the host lines of a region as {host name: normalised line}."""
        entries = {}
        for raw in body.splitlines():
            parts = raw.split()
            if parts and not parts[0].startswith("#"):
                entries[parts[1] if len(parts) > 1 else parts[0]] = " ".join(parts)
        return entries

    @staticmethod
    def _host_entries(raw):
        """Return a per-host metaData value as a dict (None when it is not one)."""
        if raw in (None, ""):
            return {}
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except ValueError:
                return None
        return raw if isinstance(raw, dict) else None

    @staticmethod
    def _group_spec(spec):
        return {
            "description": str(spec.get("description", "")),
            "template": str(spec.get("template", "")),
            "metaData": dict(spec.get("metaData") or {}),
            "osVersion": str(spec.get("osVersion", "")),
        }

    @staticmethod
    def _cluster_defaults_spec(spec):
        return {
            "description": str(spec.get("description", "")),
            "base_url": str(spec.get("base_url", "")),
            "cloud_provider": str(spec.get("cloud_provider", "")),
            "region": str(spec.get("region", "")),
            "availability_zone": str(spec.get("availability_zone", "")),
            "cluster_name": str(spec.get("cluster_name", "")),
            "short_name": str(spec.get("short_name", "")),
            "nid_length": int(spec.get("nid_length", 0) or 0),
            "public_keys": list(spec.get("public_keys") or []),
        }

    @staticmethod
    def _boot_spec(spec):
        if not isinstance(spec, dict):
            raise TypeError("Boot Service configuration spec must be a mapping")
        normalized = dict(spec)
        macs = normalized.get("macs") or []
        if not isinstance(macs, list):
            raise TypeError("Boot Service configuration spec.macs must be a list")
        normalized["macs"] = sorted(normalize_mac(value) for value in macs)
        return normalized

    def _verify_boot_configurations(self, desired):
        existing_by_name = {}
        for resource in self.boot.boot_configurations():
            name = str(resource.get("metadata", {}).get("name", "")).strip()
            if name:
                existing_by_name.setdefault(name, []).append(resource)

        for item in desired:
            name, desired_spec = self._desired_resource(
                item, "Boot Service configuration"
            )
            matches = existing_by_name.get(name, [])
            if len(matches) != 1:
                raise ValueError(
                    "Boot Service must contain exactly one configuration named "
                    f"{name!r}; found {len(matches)}"
                )
            if self._boot_spec(matches[0].get("spec") or {}) != self._boot_spec(
                desired_spec
            ):
                raise ValueError(
                    f"Boot Service configuration {name!r} does not match desired spec"
                )

    def _verify_metadata_groups(self, desired, ownership):
        existing = self._resources_by_name(
            self.metadata.groups(), "Metadata Service group"
        )
        for item in desired:
            name, desired_spec = self._desired_resource(item, "group")
            current = existing.get(name)
            if current is None:
                raise ValueError(
                    f"Metadata Service did not persist desired group {name!r}"
                )
            if self._group_spec(current.get("spec") or {}) != self._group_spec(
                desired_spec
            ):
                raise ValueError(
                    f"Metadata Service group {name!r} does not match desired spec"
                )
            if not self._has_ownership(current, ownership):
                raise ValueError(
                    f"Metadata Service group {name!r} is missing Omnia ownership labels"
                )
            status = current.get("status") or {}
            error_message = status.get("errorMessage") or status.get("errorDetails")
            if status.get("valid") is False and error_message:
                raise ValueError(
                    f"Metadata Service group {name!r} is invalid: {error_message}"
                )

    def _verify_cluster_defaults(
        self, name, desired_spec, ownership, expected_uid=None
    ):
        matches = [
            resource
            for resource in self.metadata.cluster_defaults()
            if str(resource.get("metadata", {}).get("name", "")).strip() == name
        ]
        if expected_uid:
            matches = [
                resource
                for resource in matches
                if str(resource.get("metadata", {}).get("uid", "")).strip()
                == expected_uid
            ]
        if not matches:
            raise ValueError(
                f"Metadata Service did not persist ClusterDefaults {name!r}"
            )
        current = matches[0]
        if self._cluster_defaults_spec(
            current.get("spec") or {}
        ) != self._cluster_defaults_spec(desired_spec):
            raise ValueError(
                f"Metadata Service ClusterDefaults {name!r} does not match desired spec"
            )
        if not self._has_ownership(current, ownership):
            raise ValueError(
                f"Metadata Service ClusterDefaults {name!r} is missing "
                "Omnia ownership labels"
            )

    @staticmethod
    def _unique(values) -> list[str]:
        return list(dict.fromkeys(str(value).strip() for value in values if value))
