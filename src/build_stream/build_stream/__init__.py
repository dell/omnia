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

"""build_stream package shim — redirects imports to app/ subdirectory.

After domain segregation, all Python source lives under ``app/``.
This shim allows existing ``from build_stream.core...`` imports to
continue working by extending this package's search path to include
the ``app/`` directory.

This file is NOT deployed to NFS — it only exists for local test
compatibility and IDE support.
"""

import os as _os
import sys as _sys

_APP_DIR = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "app")

if _APP_DIR not in _sys.path:
    _sys.path.insert(0, _APP_DIR)

# Extend this package's __path__ so sub-packages (core, api, etc.)
# are found under app/ when imported as build_stream.core, etc.
__path__.append(_APP_DIR)  # type: ignore[has-type]
