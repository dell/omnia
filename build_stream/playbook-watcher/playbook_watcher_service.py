#!/usr/bin/env python3
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

"""Playbook Watcher Service for OIM Core Container.

This service monitors the NFS playbook request queue, executes Ansible playbooks,
and writes results back to the results queue. It is designed to be stateless and
run as a systemd service in the OIM Core container.

Architecture:
- Polls /opt/omnia/playbook_queue/requests/ every 2 seconds
- Moves requests to processing/ to prevent duplicate execution
- Executes ansible-playbook with timeout and error handling
- Writes structured results to /opt/omnia/playbook_queue/results/
- Supports max 5 concurrent playbook executions
"""

import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread, Semaphore
from typing import Dict, Optional, Any

# Configuration
QUEUE_BASE = Path(os.getenv("PLAYBOOK_QUEUE_BASE", "/opt/omnia/playbook_queue"))
REQUESTS_DIR = QUEUE_BASE / "requests"
RESULTS_DIR = QUEUE_BASE / "results"
PROCESSING_DIR = QUEUE_BASE / "processing"
ARCHIVE_DIR = QUEUE_BASE / "archive"

POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "2"))
MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "5"))
DEFAULT_TIMEOUT_MINUTES = int(os.getenv("DEFAULT_TIMEOUT_MINUTES", "30"))

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("playbook_watcher")

# Global state
shutdown_requested = False
job_semaphore = Semaphore(MAX_CONCURRENT_JOBS)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


def ensure_directories():
    """Ensure all required directories exist with proper permissions."""
    directories = [
        REQUESTS_DIR,
        RESULTS_DIR,
        PROCESSING_DIR,
        ARCHIVE_DIR,
        ARCHIVE_DIR / "requests",
        ARCHIVE_DIR / "results",
    ]
    
    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {e}")
            raise


def parse_request_file(request_path: Path) -> Optional[Dict[str, Any]]:
    """Parse and validate request file.
    
    Args:
        request_path: Path to the request JSON file
        
    Returns:
        Parsed request dictionary or None if invalid
    """
    try:
        with open(request_path, 'r', encoding='utf-8') as f:
            request_data = json.load(f)
        
        # Validate required fields
        required_fields = ["job_id", "stage_name", "playbook_path"]
        missing_fields = [field for field in required_fields if field not in request_data]
        
        if missing_fields:
            logger.error(
                f"Request file {request_path.name} missing required fields: {missing_fields}"
            )
            return None
        
        # Set defaults
        request_data.setdefault("timeout_minutes", DEFAULT_TIMEOUT_MINUTES)
        request_data.setdefault("extra_vars", {})
        request_data.setdefault("correlation_id", request_data["job_id"])
        
        logger.info(
            f"Parsed request: job_id={request_data['job_id']}, "
            f"stage={request_data['stage_name']}, "
            f"correlation_id={request_data.get('correlation_id')}"
        )
        
        return request_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request file {request_path.name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error parsing request file {request_path.name}: {e}")
        return None


def execute_playbook(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Ansible playbook and capture results.
    
    Args:
        request_data: Parsed request dictionary
        
    Returns:
        Result dictionary with execution details
    """
    job_id = request_data["job_id"]
    stage_name = request_data["stage_name"]
    playbook_path = request_data["playbook_path"]
    extra_vars = request_data.get("extra_vars", {})
    timeout_minutes = request_data.get("timeout_minutes", DEFAULT_TIMEOUT_MINUTES)
    correlation_id = request_data.get("correlation_id", job_id)
    
    logger.info(
        f"Executing playbook for job_id={job_id}, stage={stage_name}, "
        f"correlation_id={correlation_id}"
    )
    
    started_at = datetime.now(timezone.utc)
    
    # Build ansible-playbook command
    cmd = ["ansible-playbook", playbook_path]
    
    # Add extra vars if provided
    if extra_vars:
        extra_vars_json = json.dumps(extra_vars)
        cmd.extend(["--extra-vars", extra_vars_json])
    
    # Add verbosity for debugging
    cmd.append("-v")
    
    logger.debug(f"Executing command: {' '.join(cmd)}")
    
    try:
        # Execute playbook with timeout
        timeout_seconds = timeout_minutes * 60
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False
        )
        
        completed_at = datetime.now(timezone.utc)
        duration_seconds = (completed_at - started_at).total_seconds()
        
        # Determine status
        status = "success" if result.returncode == 0 else "failed"
        
        logger.info(
            f"Playbook execution completed: job_id={job_id}, "
            f"status={status}, exit_code={result.returncode}, "
            f"duration={duration_seconds:.2f}s"
        )
        
        # Build result dictionary
        result_data = {
            "job_id": job_id,
            "stage_name": stage_name,
            "request_id": request_data.get("request_id", job_id),
            "correlation_id": correlation_id,
            "status": status,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": int(duration_seconds),
            "timestamp": completed_at.isoformat(),
        }
        
        # Add error details if failed
        if status == "failed":
            result_data["error_code"] = "PLAYBOOK_EXECUTION_FAILED"
            result_data["error_summary"] = f"Playbook exited with code {result.returncode}"
        
        return result_data
        
    except subprocess.TimeoutExpired:
        completed_at = datetime.now(timezone.utc)
        duration_seconds = (completed_at - started_at).total_seconds()
        
        logger.error(
            f"Playbook execution timed out: job_id={job_id}, "
            f"timeout={timeout_minutes}m"
        )
        
        return {
            "job_id": job_id,
            "stage_name": stage_name,
            "request_id": request_data.get("request_id", job_id),
            "correlation_id": correlation_id,
            "status": "failed",
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Playbook execution timed out after {timeout_minutes} minutes",
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": int(duration_seconds),
            "error_code": "PLAYBOOK_TIMEOUT",
            "error_summary": f"Execution exceeded timeout of {timeout_minutes} minutes",
            "timestamp": completed_at.isoformat(),
        }
        
    except Exception as e:
        completed_at = datetime.now(timezone.utc)
        duration_seconds = (completed_at - started_at).total_seconds()
        
        logger.exception(
            f"Unexpected error executing playbook: job_id={job_id}, error={e}"
        )
        
        return {
            "job_id": job_id,
            "stage_name": stage_name,
            "request_id": request_data.get("request_id", job_id),
            "correlation_id": correlation_id,
            "status": "failed",
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": int(duration_seconds),
            "error_code": "SYSTEM_ERROR",
            "error_summary": f"System error during execution: {str(e)}",
            "timestamp": completed_at.isoformat(),
        }


def write_result_file(result_data: Dict[str, Any], original_filename: str) -> bool:
    """Write result file to results directory.
    
    Args:
        result_data: Result dictionary to write
        original_filename: Original request filename for correlation
        
    Returns:
        True if successful, False otherwise
    """
    job_id = result_data["job_id"]
    
    try:
        # Use same filename pattern as request for easy correlation
        result_filename = original_filename
        result_path = RESULTS_DIR / result_filename
        
        # Write atomically using temp file
        temp_path = result_path.with_suffix('.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2)
        
        # Atomic rename
        temp_path.rename(result_path)
        
        logger.info(f"Wrote result file: {result_filename}, job_id={job_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to write result file for job_id={job_id}: {e}")
        return False


def archive_request_file(request_path: Path) -> None:
    """Archive processed request file.
    
    Args:
        request_path: Path to the request file to archive
    """
    try:
        archive_path = ARCHIVE_DIR / "requests" / request_path.name
        shutil.move(str(request_path), str(archive_path))
        logger.debug(f"Archived request file: {request_path.name}")
    except Exception as e:
        logger.warning(f"Failed to archive request file {request_path.name}: {e}")


def process_request(request_path: Path) -> None:
    """Process a single request file.
    
    This function handles the complete lifecycle of a request:
    1. Move to processing directory (atomic lock)
    2. Parse request
    3. Execute playbook
    4. Write result
    5. Archive request
    
    Args:
        request_path: Path to the request file
    """
    request_filename = request_path.name
    processing_path = PROCESSING_DIR / request_filename
    
    try:
        # Acquire semaphore for concurrency control
        job_semaphore.acquire()
        
        try:
            # Move to processing directory (atomic lock)
            try:
                shutil.move(str(request_path), str(processing_path))
                logger.debug(f"Moved request to processing: {request_filename}")
            except FileNotFoundError:
                # File already moved by another process
                logger.debug(f"Request already being processed: {request_filename}")
                return
            
            # Parse request
            request_data = parse_request_file(processing_path)
            if not request_data:
                logger.error(f"Invalid request file: {request_filename}")
                # Write error result
                error_result = {
                    "job_id": "unknown",
                    "stage_name": "unknown",
                    "status": "failed",
                    "exit_code": -1,
                    "error_code": "INVALID_REQUEST",
                    "error_summary": "Failed to parse request file",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                write_result_file(error_result, request_filename)
                archive_request_file(processing_path)
                return
            
            # Execute playbook
            result_data = execute_playbook(request_data)
            
            # Write result
            write_result_file(result_data, request_filename)
            
            # Archive request
            archive_request_file(processing_path)
            
        finally:
            # Ensure processing file is cleaned up even on error
            if processing_path.exists():
                try:
                    processing_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to remove processing file {request_filename}: {e}")
    
    finally:
        # Release semaphore
        job_semaphore.release()


def process_request_async(request_path: Path) -> None:
    """Process request in a separate thread.
    
    Args:
        request_path: Path to the request file
    """
    thread = Thread(target=process_request, args=(request_path,), daemon=True)
    thread.start()


def scan_and_process_requests() -> int:
    """Scan requests directory and process new requests.
    
    Returns:
        Number of requests processed
    """
    try:
        request_files = sorted(REQUESTS_DIR.glob("*.json"))
        
        if not request_files:
            return 0
        
        logger.debug(f"Found {len(request_files)} request file(s)")
        
        processed_count = 0
        for request_path in request_files:
            if shutdown_requested:
                logger.info("Shutdown requested, stopping request processing")
                break
            
            try:
                # Process asynchronously
                process_request_async(request_path)
                processed_count += 1
            except Exception as e:
                logger.error(f"Error processing request {request_path.name}: {e}")
        
        return processed_count
        
    except Exception as e:
        logger.error(f"Error scanning requests directory: {e}")
        return 0


def run_watcher_loop():
    """Main watcher loop that continuously polls for requests."""
    logger.info("Starting Playbook Watcher Service")
    logger.info(f"Queue base: {QUEUE_BASE}")
    logger.info(f"Poll interval: {POLL_INTERVAL_SECONDS}s")
    logger.info(f"Max concurrent jobs: {MAX_CONCURRENT_JOBS}")
    logger.info(f"Default timeout: {DEFAULT_TIMEOUT_MINUTES}m")
    
    # Ensure directories exist
    try:
        ensure_directories()
    except Exception as e:
        logger.critical(f"Failed to initialize directories: {e}")
        sys.exit(1)
    
    # Main loop
    iteration = 0
    while not shutdown_requested:
        iteration += 1
        
        try:
            processed_count = scan_and_process_requests()
            
            if processed_count > 0:
                logger.info(f"Processed {processed_count} request(s) in iteration {iteration}")
            
        except Exception as e:
            logger.exception(f"Unexpected error in watcher loop iteration {iteration}: {e}")
        
        # Sleep before next poll
        time.sleep(POLL_INTERVAL_SECONDS)
    
    logger.info("Playbook Watcher Service stopped")


def main():
    """Main entry point for the watcher service."""
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        run_watcher_loop()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.critical(f"Fatal error in watcher service: {e}")
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
