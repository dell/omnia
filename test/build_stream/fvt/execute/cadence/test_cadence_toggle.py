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

"""
Execute — Cadence Enable/Disable Applied Live.

cadence_manager reloads build_stream_config.yml at the start of every
cycle, so cadence.enabled changes apply without restarting
playbook-watcher. Neither test restarts any service:
  disable   cadence.enabled: false -> trigger -> "Cadence polling is
            disabled" logged, no catalog fetch, repo sync or commit, and
            GitLab gets no cadence_catalog_rhel.json commit and no pipeline
  re-enable watcher brought to disabled (one skipped cycle), then
            cadence.enabled: true -> trigger -> reload logs
            "enabled False -> True", the cycle runs to completion and its
            commit starts the cadence pipeline and a BuildStream job
Each test restores cadence.enabled to its original value. The re-enable
test stops at the BuildStream job and leaves the cadence pipeline running
(the full cadence run is verified by test_cadence.py); the next suite's
busy-pipeline check cancels it when pipeline.allow_pipeline_cancel is true.
The re-enabled cycle uses installation.cadence_catalog.
Markers: pipeline, cadence, sanity.
"""

import pytest

from library.functions import (
    TestLogger,
    failure_fields,
    installation_settings,
    load_test_config,
    verify_cadence_disable_live,
    verify_cadence_reenable_live,
)
from library.vars import TEST_CASES as TC


def _report(tl, result, ok_message, failed_message):
    """Log the toggle result and assert it."""
    if result["success"]:
        tl.passed_fields(ok_message, result["fields"])
    else:
        tl.failed_fields(f"{failed_message}: {len(result['failures'])} check(s)",
                         [*result["fields"], *failure_fields(result["failures"])])
    assert result["success"], f"{failed_message}: {'; '.join(result['failures'][:5])}"


@pytest.mark.pipeline
@pytest.mark.cadence
@pytest.mark.order(40810)
def test_cadence_disable_takes_effect_live(host):
    """Disable cadence without a restart; a triggered cycle must not start cadence."""
    tc = TC["cadence_disable_takes_effect_live"]
    tl = TestLogger(tc["title"], tc["id"])
    result = verify_cadence_disable_live(
        host, installation_settings(load_test_config()), tl.info)
    _report(tl, result,
            "Cadence disable applied live: the cycle was skipped, nothing reached GitLab",
            "Cadence disable not applied live")


@pytest.mark.pipeline
@pytest.mark.cadence
@pytest.mark.order(40811)
def test_cadence_reenable_resumes_cycle(host):
    """Re-enable cadence without a restart; a triggered cycle must start cadence."""
    tc = TC["cadence_reenable_resumes_cycle"]
    tl = TestLogger(tc["title"], tc["id"])
    result = verify_cadence_reenable_live(
        host, installation_settings(load_test_config()), tl.info)
    _report(tl, result, "Cadence re-enable applied live: the cycle started the cadence pipeline",
            "Cadence re-enable not applied live")
