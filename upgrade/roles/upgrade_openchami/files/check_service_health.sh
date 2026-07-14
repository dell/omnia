#!/bin/bash
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
#
# check_service_health.sh — Second-pass recovery and health check
#
# Performs a second recovery pass on openchami.target dependencies,
# waits for stabilization, then reports final service health.
# Outputs "ALL_SERVICES_HEALTHY" if all services are OK, or
# "STILL_FAILED: <list>" with the names of unhealthy services.
#
# Usage: bash check_service_health.sh

set -o pipefail

FAILED_LIST=""
for svc in $(systemctl list-dependencies openchami.target --plain --no-pager 2>/dev/null); do
  state=$(systemctl is-active "$svc" 2>/dev/null || true)
  if [ "$state" = "failed" ]; then
    echo "Restarting failed service (pass 2): $svc"
    systemctl reset-failed "$svc" 2>/dev/null || true
    systemctl restart "$svc" 2>/dev/null || true
  elif [ "$state" = "inactive" ]; then
    svc_type=$(systemctl show -p Type --value "$svc" 2>/dev/null || true)
    if [ "$svc_type" != "oneshot" ]; then
      echo "Restarting inactive service (pass 2): $svc (type=$svc_type)"
      systemctl restart "$svc" 2>/dev/null || true
    fi
  fi
done
sleep 10
for svc in $(systemctl list-dependencies openchami.target --plain --no-pager 2>/dev/null); do
  state=$(systemctl is-active "$svc" 2>/dev/null || true)
  svc_type=$(systemctl show -p Type --value "$svc" 2>/dev/null || true)
  if [ "$state" = "failed" ] || { [ "$state" = "inactive" ] && [ "$svc_type" != "oneshot" ]; }; then
    FAILED_LIST="${FAILED_LIST}${svc}($state) "
  fi
done
if [ -z "$FAILED_LIST" ]; then
  echo "ALL_SERVICES_HEALTHY"
else
  echo "STILL_FAILED: $FAILED_LIST"
fi
