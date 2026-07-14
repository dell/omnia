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
# recover_failed_services.sh — First-pass service recovery
#
# Checks openchami.target and its dependencies. Restarts any services
# that are in 'failed' or 'inactive' (non-oneshot) state.
# Outputs "ALL_SERVICES_OK" if no recovery was needed.
#
# Usage: bash recover_failed_services.sh

set -o pipefail

RECOVERED=""
if ! systemctl is-active --quiet openchami.target 2>/dev/null; then
  echo "Starting openchami.target (was inactive)"
  systemctl reset-failed 2>/dev/null || true
  systemctl start openchami.target 2>/dev/null || true
  RECOVERED="yes"
  sleep 15
fi
for svc in $(systemctl list-dependencies openchami.target --plain --no-pager 2>/dev/null); do
  state=$(systemctl is-active "$svc" 2>/dev/null || true)
  if [ "$state" = "failed" ]; then
    echo "Restarting failed service: $svc"
    systemctl reset-failed "$svc" 2>/dev/null || true
    systemctl restart "$svc" 2>/dev/null || true
    RECOVERED="yes"
  elif [ "$state" = "inactive" ]; then
    svc_type=$(systemctl show -p Type --value "$svc" 2>/dev/null || true)
    if [ "$svc_type" != "oneshot" ]; then
      echo "Restarting inactive service: $svc (type=$svc_type)"
      systemctl restart "$svc" 2>/dev/null || true
      RECOVERED="yes"
    fi
  fi
done
[ -z "$RECOVERED" ] && echo "ALL_SERVICES_OK" || true
