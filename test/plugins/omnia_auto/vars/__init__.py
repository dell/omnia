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

"""omnia-auto — Variables (public re-exports)."""

from .common_vars import (  # noqa: F401
    configure,
    get_setting,
    init_module_root,
    get_module_root,
)

from .validation_vars import COMMANDS  # noqa: F401

from .credential_vars import (  # noqa: F401
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    ENV_OMNIA_VENV_PATH,
    DEFAULT_DATA_PATH,
    DEFAULT_PROJECT_NAME,
    VAULT_KEY_LENGTH,
    VAULT_FILE_MODE,
    VAULT_HEADER,
    VAULT_TIMEOUT,
    get_data_path,
    get_project_name,
    get_domain_input_path,
)
