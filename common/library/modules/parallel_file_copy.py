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

#!/usr/bin/python
# pylint: disable=import-error,no-name-in-module,line-too-long

"""
Ansible module for parallel copying of files.

Supports copying multiple source → destination pairs in parallel,
with logging, retries, and optional cleanup.
"""

import os
import shutil
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.local_repo.standard_logger import setup_standard_logger

# ============================================================
# Default Values
# ============================================================

DEFAULT_MAX_WORKERS = 4
DEFAULT_RETRY_COUNT = 2
DEFAULT_DELETE_EXISTING = True
PARALLEL_FILE_COPY_LOG = '/opt/omnia/log/core/playbooks/parallel_file_copy.log/'

# ============================================================
# Copy Worker Function
# ============================================================

def copy_single_file(src_file, dest_dir, retry_count, delete_existing, slogger, summary):
    """Copy one directory pair with retry support."""
    thread_name = threading.current_thread().name
    start_time = datetime.now()

    if not os.path.isfile(src_file):
        slogger.info(f"NOT COPIED - Source file missing: {src_file}")
        summary["skipped"].append(src_file)
        return

    os.makedirs(dest_dir, exist_ok=True)
    dest_file = os.path.join(dest_dir, os.path.basename(src_file))

    for attempt in range(1, retry_count + 1):
        try:
            slogger.info(f"[{thread_name}] START {start_time} Copying {src_file} (Attempt {attempt})")

            if delete_existing and os.path.exists(dest_file):
                os.remove(dest_file)
                slogger.info(f"Deleted existing file: {dest_file}")

            shutil.copy2(src_file, dest_file)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            slogger.info(f"[{thread_name}] SUCCESS {end_time} Copied {src_file} -> {dest_file} (Duration={duration:.2f}s)")

            summary["copied"].append(src_file)
            return

        except Exception as err:
            slogger.error(f"[{thread_name}] ERROR copying {src_file} (Attempt {attempt}) Reason: {err}")
            if attempt == retry_count:
                summary["failed"].append(src_file)

# ============================================================
# Main Parallel Copy Logic
# ============================================================

def execute_parallel_copy(module, copy_pairs, max_workers, retry_count, delete_existing, slogger):
    """
    Executes parallel copy for all pairs.
    Returns summary dict.
    """
    summary = {"copied": [], "skipped": [], "failed": []}
    futures = []

    slogger.info("===== PARALLEL FILE COPY STARTED =====")
    slogger.info(f"Copy pairs received: {copy_pairs}")
    slogger.info(f"Max workers: {max_workers}")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for src_dir, dest_dir in copy_pairs:

            if not os.path.isdir(src_dir):
                slogger.info(f"NOT COPIED - Source directory missing: {src_dir}")
                summary["skipped"].append(src_dir)
                continue

            files = [os.path.join(src_dir, f) for f in os.listdir(src_dir) if os.path.isfile(os.path.join(src_dir, f))]
            if not files:
                slogger.info(f"NOT COPIED - No files found in directory: {src_dir}")
                summary["skipped"].append(src_dir)
                continue

            # ⚡ Show Ansible warning for in-progress copy
            module.warn(f"Copy in progress for {src_dir} -> {dest_dir}. Please wait ...")

            slogger.info(f"Copying {len(files)} files from {src_dir} -> {dest_dir} ...")

            for file_path in files:
                futures.append(executor.submit(copy_single_file, file_path, dest_dir, retry_count, delete_existing, slogger, summary))

        # Wait for all copies to finish
        for future in as_completed(futures):
            future.result()

    slogger.info("===== PARALLEL FILE COPY FINISHED =====")
    return summary

# ============================================================
# Ansible Module Entry Point
# ============================================================

def main():
    """Main Ansible module execution entrypoint."""
    module_args = dict(
        copy_pairs=dict(type="list", required=True),
        max_workers=dict(type="int", required=False, default=DEFAULT_MAX_WORKERS),
        retry_count=dict(type="int", required=False, default=DEFAULT_RETRY_COUNT),
        delete_existing=dict(type="bool", required=False, default=DEFAULT_DELETE_EXISTING),
        slog_file=dict(type="str", required=False, default=PARALLEL_FILE_COPY_LOG),
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    copy_pairs = module.params["copy_pairs"]
    max_workers = module.params["max_workers"]
    retry_count = module.params["retry_count"]
    delete_existing = module.params["delete_existing"]
    slog_file = module.params["slog_file"]

    slogger = setup_standard_logger(slog_file)

    result = dict(changed=False, copied=[], skipped=[], failed=[])

    try:
        summary = execute_parallel_copy(module, copy_pairs, max_workers, retry_count, delete_existing, slogger)

        result["copied"] = summary["copied"]
        result["skipped"] = summary["skipped"]
        result["failed"] = summary["failed"]
        if summary["copied"]:
            result["changed"] = True

        overall_status = "SUCCESS"
        if summary["failed"] and summary["copied"]:
            overall_status = "PARTIAL"
        elif summary["failed"] and not summary["copied"]:
            overall_status = "FAILURE"

        result["overall_status"] = overall_status
        module.exit_json(**result)

    except Exception as err:
        slogger.error(f"Parallel copy execution failed: {err}")
        module.fail_json(msg=str(err), **result)

if __name__ == "__main__":
    main()
