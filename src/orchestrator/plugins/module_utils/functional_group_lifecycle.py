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

# pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-positional-arguments,too-few-public-methods,too-many-locals

"""Lifecycle mutation safety, project lock, transition journal, and recovery planner.

Implements ER-ORCH-009 FR-4.1, FR-4.2, FR-5.1, and HLD Section 5.5:
  - Exact-target add/remove/configure planning
  - Node-emptiness precheck on remove (AC-006)
  - Ownership verification and fail-closed ambiguity handling
  - Project mutation lock with anti-stale inspection (no timeout-only reclamation)
  - Transition journal tracking ordered stages and terminal results
  - Bounded recovery resuming from the first incomplete idempotent stage
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class LifecycleOperation(str, Enum):
    """Supported flexible functional group lifecycle operations."""

    ADD = "add"
    REMOVE = "remove"
    CONFIGURE = "configure"


class ConfigureScope(str, Enum):
    """Supported scopes for configure operations."""

    BOTH = "both"
    BOOT = "boot"
    CLOUD_INIT = "cloud_init"


class StageName(str, Enum):
    """Ordered lifecycle mutation stages."""

    VALIDATION = "validation"
    IMAGE_PRECHECK = "image_precheck"
    SMD_GROUP = "smd_group"
    BSS = "bss"
    METADATA = "metadata"


class TerminalResult(str, Enum):
    """Terminal outcomes of a lifecycle operation."""

    SUCCEEDED = "succeeded"
    NO_OP = "noop"
    FAILED = "failed"
    BLOCKED = "blocked"
    RECOVERY_REQUIRED = "recovery_required"


class LockStatus(str, Enum):
    """Status of the project mutation lock."""

    FREE = "free"
    LOCKED = "locked"
    BLOCKED = "blocked"
    RECOVERING = "recovering"


class LifecycleError(Exception):
    """Base exception for lifecycle mutation safety errors."""


class LockContentionError(LifecycleError):
    """Raised when the project lock is held by another active operation."""


class NodeNotEmptiedError(LifecycleError):
    """Raised when remove is requested on a group that still has mapped nodes (AC-006)."""

    def __init__(self, group_name: str, remaining_node_count: int):
        self.group_name = group_name
        self.remaining_node_count = remaining_node_count
        super().__init__(
            f"Cannot remove flexible group '{group_name}' because "
            f"{remaining_node_count} node(s) are still mapped. Remove all mapped "
            "nodes first, then retry removal."
        )


class OwnershipAmbiguityError(LifecycleError):
    """Raised when ownership of records to be removed cannot be proven."""

    def __init__(self, group_name: str, details: str = ""):
        self.group_name = group_name
        self.details = details
        message = (
            f"Cannot remove flexible group '{group_name}': ownership evidence "
            f"is missing or ambiguous. {details}".strip()
        )
        super().__init__(message)


class RecoveryRequiredError(LifecycleError):
    """Raised when a non-terminal journal requires bounded recovery before new work."""


@dataclass
class StageRecord:
    """Record of a single mutation stage execution."""

    stage: str
    status: str  # "attempted", "verified", "failed", "skipped"
    timestamp: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class JournalData:
    """Data stored in the project transition journal."""

    run_id: str
    project_name: str
    operation: str
    target_group: str
    planned_stages: list[str]
    completed_stages: list[str] = field(default_factory=list)
    stage_records: list[dict[str, Any]] = field(default_factory=list)
    terminal_result: str = ""
    start_time: str = ""
    end_time: str = ""
    input_hashes: dict[str, str] = field(default_factory=dict)
    error_message: str = ""


def compute_input_hash(data: Any) -> str:
    """Compute deterministic SHA-256 hash of structured input data."""
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class ProjectLock:
    """Project-scoped mutation lock preventing concurrent mutations (FR-5.1).

    Ensures only one mutation runs at a time for a given project. A lock is
    NOT reclaimed by timeout alone; prior owner activity is verified before
    allowing recovery.
    """

    def __init__(self, lock_file_path: Path | str):
        self.lock_path = Path(lock_file_path)

    def is_process_alive(self, pid: int) -> bool:
        """Check if the recorded process ID is currently running."""
        if pid <= 0:
            return False
        try:
            # On Unix/Windows, sending signal 0 checks process existence
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def inspect(self) -> dict[str, Any]:
        """Inspect the current lock state without modifying it."""
        if not self.lock_path.exists():
            return {"status": LockStatus.FREE.value}

        try:
            content = self.lock_path.read_text(encoding="utf-8").strip()
            data = json.loads(content)
        except (json.JSONDecodeError, OSError):
            return {
                "status": LockStatus.BLOCKED.value,
                "reason": "corrupted_lock_file",
            }

        pid = data.get("pid", 0)
        run_id = data.get("run_id", "")
        owner_active = self.is_process_alive(pid) if pid else False

        if owner_active:
            return {
                "status": LockStatus.BLOCKED.value,
                "data": data,
                "owner_active": True,
                "run_id": run_id,
            }

        # Prior owner process is inactive
        return {
            "status": LockStatus.RECOVERING.value,
            "data": data,
            "owner_active": False,
            "run_id": run_id,
        }

    def acquire(
        self,
        project_name: str,
        operation: str,
        target_group: str,
        run_id: str,
        pid: int | None = None,
        force_recovery: bool = False,
    ) -> dict[str, Any]:
        """Acquire the project mutation lock atomically with O_CREAT|O_EXCL."""
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        effective_pid = pid or (os.getppid() if hasattr(os, "getppid") else os.getpid())
        lock_data = {
            "project_name": project_name,
            "operation": operation,
            "target_group": target_group,
            "run_id": run_id,
            "pid": effective_pid,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": LockStatus.LOCKED.value,
        }
        payload = json.dumps(lock_data, indent=2).encode("utf-8")
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY

        try:
            fd = os.open(str(self.lock_path), flags, 0o600)
            try:
                os.write(fd, payload)
            finally:
                os.close(fd)
            return lock_data
        except FileExistsError as exc:
            inspection = self.inspect()
            current_status = inspection.get("status")

            if current_status == LockStatus.BLOCKED.value:
                data = inspection.get("data", {})
                raise LockContentionError(
                    f"Project lock is currently held by active process {data.get('pid')} "
                    f"running '{data.get('operation')}' on '{data.get('target_group')}' "
                    f"(run_id: {data.get('run_id')}). Concurrent mutation is blocked."
                ) from exc

            if current_status == LockStatus.RECOVERING.value and not force_recovery:
                data = inspection.get("data", {})
                raise RecoveryRequiredError(
                    f"Non-terminal lock detected from inactive process {data.get('pid')} "
                    f"for operation '{data.get('operation')}' on target "
                    f"'{data.get('target_group')}'. Bounded recovery is required before proceeding."
                ) from exc

            if force_recovery:
                try:
                    self.lock_path.unlink()
                except OSError:
                    pass
                fd = os.open(str(self.lock_path), flags, 0o600)
                try:
                    os.write(fd, payload)
                finally:
                    os.close(fd)
                return lock_data

            raise LockContentionError("Project lock could not be acquired.") from exc

    def release(self, run_id: str | None = None) -> bool:
        """Release the project mutation lock if run_id matches or unforced."""
        if not self.lock_path.exists():
            return True

        if run_id:
            try:
                content = self.lock_path.read_text(encoding="utf-8").strip()
                data = json.loads(content)
                if data.get("run_id") != run_id:
                    # Do not release someone else's lock
                    return False
            except (json.JSONDecodeError, OSError):
                pass

        try:
            self.lock_path.unlink()
            return True
        except OSError:
            return False


class TransitionJournal:
    """Transition journal for recording mutation stages and recovery evidence (FR-5.1)."""

    def __init__(self, journal_file_path: Path | str):
        self.journal_path = Path(journal_file_path)

    def read(self) -> JournalData | None:
        """Read and parse the current journal data if present."""
        if not self.journal_path.exists():
            return None
        try:
            raw = json.loads(self.journal_path.read_text(encoding="utf-8"))
            return JournalData(**raw)
        except (json.JSONDecodeError, TypeError, OSError):
            return None

    def start(
        self,
        run_id: str,
        project_name: str,
        operation: str,
        target_group: str,
        planned_stages: list[str],
        input_hashes: dict[str, str] | None = None,
        force_recovery: bool = False,
    ) -> JournalData:
        """Initialize and persist a new transition journal."""
        existing = self.read()
        if existing and not existing.terminal_result and not force_recovery:
            raise RecoveryRequiredError(
                f"Transition journal for run {existing.run_id} ({existing.operation} "
                f"on {existing.target_group}) is still in progress. "
                "Bounded recovery is required before starting a new journal."
            )

        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        journal = JournalData(
            run_id=run_id,
            project_name=project_name,
            operation=operation,
            target_group=target_group,
            planned_stages=planned_stages,
            completed_stages=[],
            stage_records=[],
            terminal_result="",
            start_time=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            input_hashes=input_hashes or {},
        )
        self._write(journal)
        return journal

    def record_stage(
        self,
        stage: str,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Record the execution outcome of an individual stage."""
        journal = self.read()
        if not journal:
            return

        valid_statuses = ("attempted", "verified", "failed", "skipped")
        if status not in valid_statuses:
            raise ValueError(
                f"Invalid stage status '{status}'. Must be one of: {', '.join(valid_statuses)}"
            )

        if journal.planned_stages and stage not in journal.planned_stages:
            raise ValueError(
                f"Stage '{stage}' is not in planned stages: {journal.planned_stages}"
            )

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        record = {
            "stage": stage,
            "status": status,
            "timestamp": now,
            "details": details or {},
        }
        journal.stage_records.append(record)

        if status == "verified" and stage not in journal.completed_stages:
            journal.completed_stages.append(stage)

        self._write(journal)

    def finish(
        self,
        terminal_result: str,
        error_message: str = "",
    ) -> JournalData | None:
        """Mark the journal with a terminal outcome and close it."""
        journal = self.read()
        if not journal:
            return None

        journal.terminal_result = terminal_result
        journal.error_message = error_message
        journal.end_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self._write(journal)
        return journal

    def _write(self, journal: JournalData) -> None:
        """Atomically persist journal data with 0600 permissions."""
        temp_path = self.journal_path.with_suffix(".tmp")
        payload = json.dumps(asdict(journal), indent=2).encode("utf-8")
        flags = os.O_CREAT | os.O_TRUNC | os.O_WRONLY
        fd = os.open(str(temp_path), flags, 0o600)
        try:
            os.write(fd, payload)
        finally:
            os.close(fd)
        temp_path.replace(self.journal_path)


class LifecyclePlanner:
    """Plans exact-target lifecycle operations with prechecks and no-op detection."""

    @staticmethod
    def plan_add(
        target_group: str,
        effective_config: dict[str, Any],
        current_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build ordered add plan for one flexible functional group (FR-4.1).

        Stages: smd_group -> bss -> metadata
        Detects no-op if current state already matches desired state.
        """
        planned_stages = [
            StageName.SMD_GROUP.value,
            StageName.BSS.value,
            StageName.METADATA.value,
        ]

        if current_state:
            # Check if all stages are already verified and matching
            smd_present = current_state.get("smd_group_present", False)
            bss_matching = current_state.get("bss_config_matching", False)
            metadata_matching = current_state.get("metadata_matching", False)

            if smd_present and bss_matching and metadata_matching:
                return {
                    "operation": LifecycleOperation.ADD.value,
                    "target_group": target_group,
                    "planned_stages": planned_stages,
                    "stages_to_execute": [],
                    "is_noop": True,
                    "reason": (
                        "Desired OpenCHAMI SMD, BSS, and metadata state already "
                        "present and matching."
                    ),
                }

        # Unused config placeholder retained for future attribute diffing
        _ = effective_config

        return {
            "operation": LifecycleOperation.ADD.value,
            "target_group": target_group,
            "planned_stages": planned_stages,
            "stages_to_execute": planned_stages,
            "is_noop": False,
        }

    @staticmethod
    def plan_remove(
        target_group: str,
        mapped_nodes: list[Any],
        all_functional_groups: list[dict[str, Any]] | None = None,
        ownership_evidence: dict[str, Any] | None = None,
        current_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build ordered remove plan for one flexible group (FR-4.2).

        Prechecks:
          1. Target group must have 0 mapped nodes in active PXE mapping (AC-006).
          2. Ownership must be proven; fails closed on ambiguity.
        Stages (ordered teardown): metadata -> bss -> smd_group
        Recalculates shared ssh/chrony groups from remaining flexible groups.
        """
        # Precheck 1: Node emptiness (AC-006)
        remaining_count = len(mapped_nodes)
        if remaining_count > 0:
            raise NodeNotEmptiedError(target_group, remaining_count)

        # Check no-op: already completely absent
        if current_state:
            smd_present = current_state.get("smd_group_present", False)
            bss_present = current_state.get("bss_present", False)
            metadata_present = current_state.get("metadata_present", False)
            if not smd_present and not bss_present and not metadata_present:
                return {
                    "operation": LifecycleOperation.REMOVE.value,
                    "target_group": target_group,
                    "planned_stages": [
                        StageName.METADATA.value,
                        StageName.BSS.value,
                        StageName.SMD_GROUP.value,
                    ],
                    "stages_to_execute": [],
                    "is_noop": True,
                    "remaining_groups": [],
                    "reason": (
                        f"Flexible group '{target_group}' has no existing "
                        "SMD, BSS, or metadata records."
                    ),
                }

        # Precheck 2: Ownership verification (fails closed if missing or ambiguous)
        if not ownership_evidence:
            raise OwnershipAmbiguityError(
                target_group,
                "ownership evidence is missing or ambiguous. No ownership evidence provided."
            )
        is_owned = ownership_evidence.get("owned", False)
        is_ambiguous = ownership_evidence.get("ambiguous", False)
        if is_ambiguous or not is_owned:
            details = ownership_evidence.get("reason", "Record owner mismatch or absent label.")
            raise OwnershipAmbiguityError(target_group, details)

        # Calculate remaining flexible groups for shared service recalculation
        all_groups = all_functional_groups or []
        remaining_groups = [
            g for g in all_groups
            if g.get("name", "").startswith("fg_") and g.get("name") != target_group
        ]

        planned_stages = [
            StageName.METADATA.value,
            StageName.BSS.value,
            StageName.SMD_GROUP.value,
        ]

        return {
            "operation": LifecycleOperation.REMOVE.value,
            "target_group": target_group,
            "planned_stages": planned_stages,
            "stages_to_execute": planned_stages,
            "is_noop": False,
            "remaining_groups": remaining_groups,
        }

    @staticmethod
    def plan_configure(
        target_group: str,
        configure_scope: str = "both",
    ) -> dict[str, Any]:
        """Build configure-only plan without lifecycle group mutations (FR-4.3)."""
        if configure_scope == ConfigureScope.BOOT.value:
            stages = [StageName.BSS.value]
        elif configure_scope == ConfigureScope.CLOUD_INIT.value:
            stages = [StageName.METADATA.value]
        else:
            stages = [StageName.BSS.value, StageName.METADATA.value]

        return {
            "operation": LifecycleOperation.CONFIGURE.value,
            "target_group": target_group,
            "configure_scope": configure_scope,
            "planned_stages": stages,
            "stages_to_execute": stages,
            "is_noop": False,
        }


class BoundedRecoveryManager:
    """Manages idempotent resumption and bounded recovery (FR-5.1)."""

    @staticmethod
    def evaluate_resumption(
        journal: JournalData,
        planned_stages: list[str],
    ) -> list[str]:
        """Determine remaining stages to execute from an interrupted journal.

        Skips stages that were already verified in the previous run.
        """
        completed = set(journal.completed_stages)
        return [stage for stage in planned_stages if stage not in completed]
