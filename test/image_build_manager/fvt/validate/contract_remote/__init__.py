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

"""Image Build Validate - remote repo_manager fetch suite.

Runs ``repo_manager`` on the external OIM (OIM1) over SSH and stages its repo_status.yml
and Pulp certificate in ``/tmp/omnia_contract_test/`` for the ``contract_build`` stage.
Needs ``external_oim`` in ``test_config.yml`` and ``external_oim_password`` in
``test_creds.yml`` (or ``SVT_EXTERNAL_OIM_PASS``).
"""
