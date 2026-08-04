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
Core input validation framework.

This package contains the core components of the input validation system:
- config: Configuration constants and paths
- file_utils: File operations and parsing
- utils: Common utility functions
- validation_engine: Main validation orchestration
"""

from ansible.module_utils.input_validation.core import config
from ansible.module_utils.input_validation.core import file_utils
from ansible.module_utils.input_validation.core import utils
from ansible.module_utils.input_validation.core import validation_engine

__all__ = ['config', 'file_utils', 'utils', 'validation_engine']
