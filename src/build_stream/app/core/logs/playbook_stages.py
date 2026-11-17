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

"""Pipeline stages that execute an Ansible playbook (ER-BSM-003).

Only these stages produce an execution log. ``parse-catalog`` and ``upload``
are handled inside the BSM API and never run a playbook.
"""

from typing import Union

from core.jobs.value_objects import StageName, StageType

PLAYBOOK_STAGES = frozenset(
    {
        StageType.CREATE_LOCAL_REPOSITORY.value,
        StageType.BUILD_IMAGE.value,
        StageType.VALIDATE.value,
        StageType.RESTART.value,
        StageType.DEPLOY.value,
    }
)


def is_playbook_stage(stage_name: Union[str, StageName]) -> bool:
    """Return True when the stage executes an Ansible playbook."""
    return str(stage_name) in PLAYBOOK_STAGES
