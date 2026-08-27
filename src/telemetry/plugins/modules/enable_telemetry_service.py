# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
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

"""
Dell iDRAC Telemetry - FAST Enable All Reports.

Optimized with parallel processing and connection pooling.
Supports iDRAC 9 and iDRAC 10.
"""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any, Tuple
import requests
import urllib3
from ansible.module_utils.basic import AnsibleModule

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
#####################################################
# ALL 37 TELEMETRY REPORTS (iDRAC 9 & 10)
#####################################################

ALL_REPORTS: List[str] = [
    "AggregationMetrics", "CPUMemMetrics", "CPURegisters",
    "CPUSensor", "MemoryMetrics", "MemorySensor",
    "NVMeSMARTData", "StorageDiskSMARTData", "StorageSensor",
    "NICSensor", "NICStatistics", "FCPortStatistics",
    "FCSensor", "SFPTransceiver", "InfiniBandStatistics",
    "PSUMetrics", "PowerMetrics", "PowerStatistics",
    "FanSensor", "ThermalMetrics", "ThermalSensor",
    "GPUMetrics", "GPUStatistics", "GPUSubsystemPower", "FPGASensor",
    "Sensor", "SerialLog", "SystemUsage", "x86SubsystemPower",
    "OME-ISM-MetricsData", "OME-PMP-Power-B",
    "OME-SFPTransceiver-Metrics", "OME-Telemetry-FCPortStatistics",
    "OME-Telemetry-GPU-Aggregate", "OME-Telemetry-GPU-Aggregate-1",
    "OME-Telemetry-NIC-Statistics", "OME-Telemetry-SMARTData",
]

def get_report_definitions(
    ip_address: str,
    user: str,
    password: str,
    session: requests.Session,
    timeout: int,
) -> Optional[List[str]]:
    """Fetch available report definitions from iDRAC."""
    url = f"https://{ip_address}/redfish/v1/TelemetryService/MetricReportDefinitions"
    try:
        response = session.get(
            url,
            auth=(user, password),
            verify=False,
            timeout=timeout,
        )
        if response.status_code == 200:
            data = response.json()
            return [
                member['@odata.id'].split('/')[-1]
                for member in data.get('Members', [])
            ]
    except (requests.exceptions.RequestException, ValueError, KeyError):
        pass
    return None


def enable_report(
    session: requests.Session,
    url: str,
    user: str,
    password: str,
    timeout: int,
) -> bool:
    """Enable a single telemetry report."""
    try:
        data = {
            "MetricReportDefinitionEnabled": True,
            "Status": {"State": "Enabled"}
        }
        response = session.patch(
            url,
            json=data,
            auth=(user, password),
            verify=False,
            timeout=timeout,
        )
        return response.status_code in [200, 202, 204]
    except requests.exceptions.RequestException:
        return False


def enable_reports_parallel(
    session: requests.Session,
    base_url: str,
    reports_to_enable: List[str],
    user: str,
    password: str,
    timeout: int,
    report_workers: int = 10,
) -> Tuple[List[str], List[str]]:
    """Enable multiple reports in parallel."""
    enabled_reports: List[str] = []
    failed_reports: List[str] = []

    report_urls = {
        report: f"{base_url}/MetricReportDefinitions/{report}"
        for report in reports_to_enable
    }

    with ThreadPoolExecutor(max_workers=report_workers) as executor:
        future_to_report = {
            executor.submit(enable_report, session, url, user, password, timeout): report
            for report, url in report_urls.items()
        }
        for future in as_completed(future_to_report):
            report_name = future_to_report[future]
            if future.result():
                enabled_reports.append(report_name)
            else:
                failed_reports.append(report_name)

    return enabled_reports, failed_reports


def configure_server(
    ip_address: str,
    user: str,
    password: str,
    timeout: int,
    exclude_reports: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Configure telemetry for a single server."""
    session = requests.Session()
    session.verify = False
    exclude_reports = exclude_reports or []

    try:
        base_url = f"https://{ip_address}/redfish/v1/TelemetryService"

        # Step 1: Enable Telemetry Service
        response = session.patch(
            base_url,
            json={"ServiceEnabled": True},
            auth=(user, password),
            timeout=timeout,
        )

        if response.status_code not in [200, 202, 204]:
            return {
                "ip": ip_address,
                "status": "failed",
                "message": f"Service HTTP {response.status_code}"
            }

        # Step 2: Get available reports
        available_reports = get_report_definitions(
            ip_address, user, password, session, timeout
        )
        if not available_reports:
            return {
                "ip": ip_address,
                "status": "failed",
                "message": "Cannot get reports"
            }

        # Step 3: Filter out excluded reports
        reports_to_enable = [
            r for r in available_reports if r not in exclude_reports
        ]
        skipped_reports = [
            r for r in available_reports if r in exclude_reports
        ]

        # Step 4: Enable reports in parallel
        enabled_reports, failed_reports = enable_reports_parallel(
            session, base_url, reports_to_enable, user, password, timeout
        )

        return {
            "ip": ip_address,
            "status": "success",
            "message": f"{len(enabled_reports)}/{len(available_reports)} enabled",
            "total_reports": len(available_reports),
            "enabled_reports": enabled_reports,
            "skipped_reports": skipped_reports,
            "failed_reports": failed_reports,
        }

    except requests.exceptions.RequestException as e:
        return {
            "ip": ip_address,
            "status": "failed",
            "message": str(e)
        }

    finally:
        try:
            session.close()
        except OSError as close_error:
            logging.warning("Warning: failed to close session for %s: %s", ip_address, close_error)

def run_parallel(
    idrac_ips: List[str],
    username: str,
    password: str,
    parallel_jobs: int,
    timeout: int,
    exclude_reports: Optional[List[str]] = None,
) -> Tuple[List[Dict], List[Dict]]:
    """Run telemetry configuration in parallel."""
    success_results = []
    failed_results = []

    try:
        workers = max(1, min(os.cpu_count() + 1, parallel_jobs))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_ip = {
                executor.submit(
                    configure_server, ip, username, password, timeout, exclude_reports
                ): ip for ip in idrac_ips
            }

            for future in as_completed(future_to_ip):
                result = future.result()
                if result.get("status") == "success":
                    success_results.append(result)
                else:
                    failed_results.append(result)
    except (OSError, ValueError, requests.exceptions.RequestException) as exc:
        logging.warning("Error during parallel execution: %s", exc)

    return success_results, failed_results

def main():
    """Main function for Ansible module."""
    module_args = {
        "idrac_ips": {"type": "list", "required": True, "elements": "str"},
        "username": {"type": "str", "required": True},
        "password": {"type": "str", "required": True, "no_log": True},
        "parallel_jobs": {"type": "int", "default": 64},
        "timeout": {"type": "int", "default": 30},
        "exclude_reports": {"type": "list", "required": False, "elements": "str", "default": []},
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    idrac_ips = module.params["idrac_ips"]
    username = module.params["username"]
    password = module.params["password"]
    parallel_jobs = module.params["parallel_jobs"]
    timeout = module.params["timeout"]
    exclude_reports = module.params["exclude_reports"]

    if module.check_mode:
        module.exit_json(changed=False, msg="Check mode - no changes made")

    if not idrac_ips:
        module.exit_json(msg="No iDRAC IPs provided")

    start_time = time.time()
    success_results, failed_results = run_parallel(
        idrac_ips, username, password, parallel_jobs, timeout, exclude_reports
    )

    duration = time.time() - start_time

    # Calculate total reports enabled/failed
    total_enabled = sum(len(r.get("enabled_reports", [])) for r in success_results)
    total_failed = sum(len(r.get("failed_reports", [])) for r in success_results)
    total_skipped = sum(len(r.get("skipped_reports", [])) for r in success_results)

    module.exit_json(
        changed=len(success_results) > 0,
        success_count=len(success_results),
        failed_count=len(failed_results),
        total_reports_enabled=total_enabled,
        total_reports_failed=total_failed,
        total_reports_skipped=total_skipped,
        duration_seconds=round(duration, 2),
        success_results=success_results,
        failed_results=failed_results,
        msg=f"Telemetry enabled on {len(success_results)}/{len(idrac_ips)} servers ({total_enabled} reports)"
    )

if __name__ == "__main__":
    main()
