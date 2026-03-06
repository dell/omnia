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

"""Secure logging utilities for Build Stream API.

Provides per-job file logging with automatic redaction of sensitive data
(IP addresses, JWT tokens, passwords, API keys, emails) so that job log
files never contain exploitable information.
"""

import logging
import re
import traceback
from pathlib import Path
from typing import Dict, Optional

_LOG_FORMATTER = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

_LOG_BASE = Path("/opt/omnia/log/build_stream")

_job_loggers: Dict[str, logging.Logger] = {}

# ---------------------------------------------------------------------------
# Sensitive-data redaction patterns
# ---------------------------------------------------------------------------
_SENSITIVE_PATTERNS = [
    # IPv4 addresses  (e.g. 192.168.1.100)
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "<REDACTED_IP>"),
    # IPv6 addresses  (simplified – colon-hex groups)
    (re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4}\b"), "<REDACTED_IP>"),
    # JWT / Bearer tokens  (three base64url segments separated by dots)
    (re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"), "<REDACTED_TOKEN>"),
    # Authorization header values
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9_\-\.]+"), r"\1<REDACTED_TOKEN>"),
    # password= or passwd= or secret= or api_key= or token= values
    (re.compile(
        r"(?i)((?:password|passwd|secret|api_key|apikey|token|auth_token)"
        r"\s*[=:]\s*)[^\s,;\"']+"
    ), r"\1<REDACTED>"),
    # Email addresses
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "<REDACTED_EMAIL>"),
]


def _sanitize_message(message: str) -> str:
    """Redact sensitive data from a log message."""
    for pattern, replacement in _SENSITIVE_PATTERNS:
        message = pattern.sub(replacement, message)
    return message


# ---------------------------------------------------------------------------
# Job log-file lifecycle
# ---------------------------------------------------------------------------
def create_job_log_file(job_id: str) -> Optional[Path]:
    """Create ``<LOG_BASE>/<job_id>/<job_id>.log`` and warm the cached logger.

    Called once from the create-job API.  Subsequent calls to
    :func:`log_secure_info` with the same *job_id* will append to this file.

    Returns:
        Path to the created log file, or ``None`` on failure.
    """
    job_log_dir = _LOG_BASE / job_id
    try:
        job_log_dir.mkdir(parents=True, exist_ok=True)
        log_file = job_log_dir / f"{job_id}.log"
        log_file.touch(exist_ok=True)
        _get_or_create_job_logger(job_id, log_file)
        return log_file
    except OSError:
        logging.getLogger(__name__).warning(
            "Failed to create job log directory/file for job: %s", job_id
        )
        return None


def remove_job_logger(job_id: str) -> None:
    """Flush, close, and remove the cached logger for *job_id*."""
    job_logger = _job_loggers.pop(job_id, None)
    if job_logger is None:
        return
    for handler in list(job_logger.handlers):
        handler.flush()
        handler.close()
        job_logger.removeHandler(handler)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _get_job_log_file(job_id: str) -> Optional[Path]:
    """Return the Path to the job log file if the directory exists."""
    log_file = _LOG_BASE / job_id / f"{job_id}.log"
    if log_file.parent.is_dir():
        return log_file
    return None


def _get_or_create_job_logger(
    job_id: str, log_file: Optional[Path] = None
) -> Optional[logging.Logger]:
    """Return a cached per-job logger, creating one if necessary."""
    if job_id in _job_loggers:
        return _job_loggers[job_id]

    if log_file is None:
        log_file = _get_job_log_file(job_id)
    if log_file is None:
        return None

    try:
        job_logger = logging.getLogger(f"build_stream.job.{job_id}")
        job_logger.setLevel(logging.DEBUG)
        job_logger.propagate = False
        handler = logging.FileHandler(str(log_file), mode="a")
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(_LOG_FORMATTER)
        job_logger.addHandler(handler)
        _job_loggers[job_id] = job_logger
        return job_logger
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Auth log file (singleton)
# ---------------------------------------------------------------------------
_auth_logger: Optional[logging.Logger] = None


def _get_or_create_auth_logger() -> Optional[logging.Logger]:
    """Return the cached auth logger, creating it on first call.

    Writes to ``<LOG_BASE>/auth.log``.
    """
    global _auth_logger  # pylint: disable=global-statement
    if _auth_logger is not None:
        return _auth_logger

    try:
        _LOG_BASE.mkdir(parents=True, exist_ok=True)
        log_file = _LOG_BASE / "auth.log"
        log_file.touch(exist_ok=True)

        auth_logger = logging.getLogger("build_stream.auth")
        auth_logger.setLevel(logging.DEBUG)
        auth_logger.propagate = False
        handler = logging.FileHandler(str(log_file), mode="a")
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(_LOG_FORMATTER)
        auth_logger.addHandler(handler)
        _auth_logger = auth_logger
        return _auth_logger
    except OSError:
        logging.getLogger(__name__).warning("Failed to create auth log file")
        return None


_SEPARATOR = "-" * 80


def log_auth_info(
    level: str,
    message: str,
    exc_info: bool = False,
    end_section: bool = False,
) -> None:
    """Log an auth/register event to ``<LOG_BASE>/auth.log``.

    Sensitive data is automatically redacted before writing.

    Args:
        level: ``'info'``, ``'warning'``, ``'error'``, ``'debug'``, or ``'critical'``.
        message: Human-readable log message.
        exc_info: Append the current exception traceback.
        end_section: Append a separator line to visually delimit this execution.
    """
    logger = logging.getLogger(__name__)

    log_message = message
    if exc_info:
        log_message = f"{log_message}\n{traceback.format_exc().rstrip()}"

    log_message = _sanitize_message(log_message)

    log_func = getattr(logger, level, logger.info)
    log_func(log_message)

    auth_logger = _get_or_create_auth_logger()
    if auth_logger:
        auth_log_func = getattr(auth_logger, level, auth_logger.info)
        auth_log_func(log_message)
        if end_section:
            auth_logger.info(_SEPARATOR)


# ---------------------------------------------------------------------------
# Public logging entry point (per-job)
# ---------------------------------------------------------------------------
def log_secure_info(
    level: str,
    message: str,
    identifier: Optional[str] = None,
    job_id: Optional[str] = None,
    exc_info: bool = False,
    end_section: bool = False,
) -> None:
    """Log a message after redacting sensitive data.

    * *identifier* is truncated to its first 8 characters.
    * IP addresses, JWT tokens, passwords, API keys, and emails are
      automatically replaced with ``<REDACTED_*>`` placeholders.
    * When *job_id* is supplied the entry is also written to the
      per-job log file.

    Args:
        level: ``'info'``, ``'warning'``, ``'error'``, ``'debug'``, or ``'critical'``.
        message: Human-readable log message.
        identifier: Optional opaque id — only the first 8 chars are kept.
        job_id: Route the entry to the job-specific log file.
        exc_info: Append the current exception traceback.
        end_section: Append a separator line to visually delimit this execution.
    """
    logger = logging.getLogger(__name__)

    if identifier:
        log_message = f"{message}: {identifier[:8]}..."
    else:
        log_message = message

    if exc_info:
        log_message = f"{log_message}\n{traceback.format_exc().rstrip()}"

    log_message = _sanitize_message(log_message)

    log_func = getattr(logger, level, logger.info)
    log_func(log_message)

    if job_id:
        job_logger = _get_or_create_job_logger(job_id)
        if job_logger:
            job_log_func = getattr(job_logger, level, job_logger.info)
            job_log_func(log_message)
            if end_section:
                job_logger.info(_SEPARATOR)
