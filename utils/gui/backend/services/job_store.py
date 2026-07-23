"""Job store for tracking background job state.
Provides thread-safe storage for job progress tracking.
Replaces module-level _jobs dict with proper encapsulation.
"""
import threading
import time
import uuid
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TooManyConcurrentJobsError(Exception):
    """Raised when the concurrent job limit is reached."""


class JobStore:
    """Thread-safe store for background job state."""

    # Fields the worker is known to send (audit via: grep -rn "update_job")
    _KNOWN_FIELDS = frozenset({
        "status", "progress", "error", "result",
    })

    _VALID_TRANSITIONS = {
        "pending":     {"in_progress", "failed"},
        "in_progress": {"completed", "failed"},
        "completed":   set(),
        "failed":      set(),
    }

    _VALID_STATUSES = frozenset(_VALID_TRANSITIONS.keys())

    def __init__(self, max_concurrent_jobs: int = 3):
        """Initialize job store.

        Args:
            max_concurrent_jobs: Maximum number of concurrent jobs allowed

        Raises:
            ValueError: If max_concurrent_jobs is less than 1
        """
        if max_concurrent_jobs < 1:
            raise ValueError(
                f"max_concurrent_jobs must be >= 1, got {max_concurrent_jobs}"
            )
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._max_concurrent_jobs = max_concurrent_jobs

    @property
    def max_concurrent_jobs(self) -> int:
        """Maximum number of concurrent jobs allowed."""
        return self._max_concurrent_jobs

    def __repr__(self) -> str:
        # No lock — avoids deadlock when repr is called from logger/debugger
        return (
            f"JobStore(jobs={len(self._jobs)}, "
            f"max={self._max_concurrent_jobs})"
        )

    def create_job(self) -> str:
        """Create a new job with concurrency limit.

        Returns:
            Job ID string

        Raises:
            TooManyConcurrentJobsError: If concurrent job limit reached
        """
        with self._lock:
            active = sum(
                1 for j in self._jobs.values()
                if j["status"] in ("pending", "running")
            )
            if active >= self._max_concurrent_jobs:
                raise TooManyConcurrentJobsError(
                    f"Limit of {self._max_concurrent_jobs} concurrent jobs reached"
                )
            job_id = str(uuid.uuid4())
            self._jobs[job_id] = {
                "status": "pending",
                "progress": 0,
                "error": None,
                "created_at": time.time(),
            }
        logger.debug("Created job %s", job_id)
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a snapshot copy of job state.

        Args:
            job_id: Job identifier

        Returns:
            Job state dictionary or None if not found
        """
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def update_job(self, job_id: str, **fields) -> None:
        """Atomically update job fields.

        Warns on unexpected fields instead of crashing, so background
        worker threads are never killed silently.

        Args:
            job_id: Job identifier
            **fields: Fields to update (status, progress, error, result)

        Raises:
            KeyError: If job_id not found
        """
        # --- Stateless validation (warn, don't crash) ---
        unexpected = set(fields) - self._KNOWN_FIELDS
        if unexpected:
            logger.warning(
                "Unexpected field(s) in update_job for %s: %s",
                job_id, unexpected,
            )

        if "progress" in fields:
            p = fields["progress"]
            if isinstance(p, bool) or not isinstance(p, (int, float)):
                logger.warning(
                    "Invalid progress type for job %s: %r", job_id, p,
                )
                fields.pop("progress")
            else:
                fields["progress"] = max(0, min(100, int(p)))

        # --- Stateful validation + update (under lock) ---
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(f"Job not found: {job_id!r}")

            job = self._jobs[job_id]

            if "status" in fields:
                new_status = fields["status"]
                allowed = self._VALID_TRANSITIONS.get(job["status"], set())
                if new_status not in allowed:
                    logger.warning(
                        "Invalid transition for job %s: %r → %r",
                        job_id, job["status"], new_status,
                    )
                    fields.pop("status")
                elif new_status in ("completed", "failed"):
                    job["finished_at"] = time.time()

            job.update(fields)
        logger.debug("Updated job %s with fields: %s", job_id, set(fields.keys()))

    def delete_job(self, job_id: str) -> bool:
        """Delete a job from the store.

        Args:
            job_id: Job identifier

        Returns:
            True if job was deleted, False if not found

        Raises:
            ValueError: If job is in pending or running state
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            if job["status"] in ("pending", "running"):
                raise ValueError(
                    f"Cannot delete job {job_id!r} in state {job['status']!r}"
                )
            del self._jobs[job_id]
        logger.debug("Deleted job %s", job_id)
        return True

    def list_jobs(self, status: Optional[str] = None) -> list[Dict[str, Any]]:
        """Return snapshot list of all jobs, optionally filtered by status.

        Args:
            status: Optional status filter

        Returns:
            List of job state dictionaries with job_id included

        Raises:
            ValueError: If status filter is invalid
        """
        if status is not None and status not in self._VALID_STATUSES:
            raise ValueError(f"Invalid status filter: {status!r}")
        with self._lock:
            return [
                {"job_id": jid, **dict(j)}
                for jid, j in self._jobs.items()
                if status is None or j["status"] == status
            ]

    def cleanup(self, max_age_seconds: float = 3600) -> int:
        """Remove terminal jobs older than max_age_seconds.

        Args:
            max_age_seconds: Maximum age in seconds for terminal jobs

        Returns:
            Number of jobs removed
        """
        cutoff = time.time() - max_age_seconds
        with self._lock:
            stale = [
                jid for jid, j in self._jobs.items()
                if j["status"] in ("completed", "failed")
                and j.get("finished_at", j["created_at"]) < cutoff
            ]
            for jid in stale:
                del self._jobs[jid]
        if stale:
            logger.info("Cleaned up %d stale jobs", len(stale))
        return len(stale)