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

from collections.abc import Iterable
from typing import Any

from .client import BootServiceClient, MetadataClient, OpenChamiClient, SMDClient
from .discovery import StaticDiscovery
from .identity import SMDIdentityResolver, normalize_mac


class OpenChamiReconciler:
    """Coordinate identity, SMD, and Metadata Service operations."""

    MANAGED_BY_LABEL = "omnia.dell.com/managed-by"
    PROJECT_LABEL = "omnia.dell.com/project"
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
                "metadata": {"name": name},
                "spec": desired_spec,
                "labels": ownership,
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
                (updated if spec_changed else adopted).append(name)
            else:
                unchanged.append(name)

        if not check_mode:
            self._verify_metadata_groups(desired, ownership)
        return {
            "changed": bool(created or updated or adopted),
            "created": created,
            "updated": updated,
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
            "metadata": {"name": name},
            "spec": desired_spec,
            "labels": ownership,
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
                            "metadata": {"name": instance_id},
                            "spec": desired_spec,
                            "labels": ownership,
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
                            "metadata": {"name": instance_id},
                            "spec": merged_spec,
                            "labels": ownership,
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
