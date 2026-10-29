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
Installation — Cadence Enable/Disable Applied Live.

cadence_manager reloads build_stream_config.yml at the start of every
cycle, so cadence.enabled changes apply without restarting
playbook-watcher. Neither test restarts any service:
  disable   cadence.enabled: false -> trigger -> "Cadence polling is
            disabled" logged, no catalog fetch, repo sync or commit
  re-enable watcher brought to disabled (one skipped cycle), then
            cadence.enabled: true -> trigger -> reload logs
            "enabled False -> True" and the cycle runs to completion
Each test restores cadence.enabled to its original value. They do not
depend on the build pipeline (cadence syncs repositories on its own).
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


@pytest.mark.svt
@pytest.mark.br_86010
@pytest.mark.installation
@pytest.mark.cadence
@pytest.mark.sanity
@pytest.mark.order(2601)
def test_cadence_disable_takes_effect_live(host):
    """Disable cadence without a restart; the next triggered cycle is skipped."""
    tc = TC["cadence_disable_takes_effect_live"]
    tl = TestLogger(tc["title"], tc["id"])
    result = verify_cadence_disable_live(
        host, installation_settings(load_test_config()), tl.info)
    _report(tl, result, "Cadence disable applied live: the triggered cycle was skipped",
            "Cadence disable not applied live")


@pytest.mark.svt
@pytest.mark.br_86010
@pytest.mark.installation
@pytest.mark.cadence
@pytest.mark.sanity
@pytest.mark.order(2602)
def test_cadence_reenable_resumes_cycle(host):
    """Re-enable cadence without a restart; a triggered cycle runs to completion."""
    tc = TC["cadence_reenable_resumes_cycle"]
    tl = TestLogger(tc["title"], tc["id"])
    result = verify_cadence_reenable_live(
        host, installation_settings(load_test_config()), tl.info)
    _report(tl, result, "Cadence re-enable applied live: the cycle ran to completion",
            "Cadence re-enable not applied live")
