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

"""Image Build Validate — External repo_manager Contract suite.

**Data-source categories (23 tests total):**

==========  ====================  ==========================================
Category    Tests                 Data source
==========  ====================  ==========================================
Synthetic   V005-V017, V020,      ``minimal_external_status()`` — hand-built
fixtures    V021, V023, V024      dicts in ``contract_func.py``
            (19 tests)
Bundled     V018, V019            ``load_sample_status()`` reading
samples     (2 tests)             ``src/.../samples/repo_manager_output/``
Live file   **E002, E003, E004,   ``live_status_path()`` → the actual
            V022** (4 tests)      ``repo_status.yml`` a real repo_manager
                                  run produces
==========  ====================  ==========================================

**"23 passed" alone is not sufficient evidence** that the external-source
contract was validated.  Check the skip count: if any of the 4 live-file
tests were skipped, the contract was only validated against synthetic and
bundled data, not the real deployment output.

To guarantee the live-file tests run:

* In CI / nightly pipelines, set ``REQUIRE_LIVE_REPO_STATUS=1``.
  This turns skips into failures so a green gate proves all 4 ran.
* The SVT ``external_contract`` theme sets ``REQUIRE_LIVE_REPO_STATUS=1``
  for the ``contract_build`` stage, so the gate fails if the file is
  missing.  The theme depends on a completed ``repo_manager`` run from
  an external source before this suite runs.

**Repo Manager dependency:**

This suite does not trigger a ``repo_manager`` execution itself.  It
depends on the file already being present from an earlier stage or run.
The SVT ``external_contract`` theme satisfies this by running
``contract_prepare`` (which includes ``--tags prepare``) before
``contract_build``.  For standalone FVT runs, ensure a ``repo_manager``
run has completed and produced ``repo_status.yml`` at the expected path.
"""
