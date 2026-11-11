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
Regression test for OMN-DEF #819.

``get_collect_output_path`` is defined in ``library/functions/host_func.py``
but must also be re-exported from ``library/functions/__init__.py`` (both the
``from .host_func import (...)`` block and ``__all__``) so that
``from library.functions import get_collect_output_path`` keeps working.
A prior regression dropped the re-export and broke every collect FVT at
import time with an ``ImportError``.
"""

# pylint: disable=missing-function-docstring,import-outside-toplevel


def test_get_collect_output_path_is_importable_from_library_functions():
    from library.functions import get_collect_output_path  # noqa: F401

    assert callable(get_collect_output_path)


def test_get_collect_output_path_is_declared_in_all():
    import library.functions as library_functions

    assert "get_collect_output_path" in library_functions.__all__


def test_get_collect_output_path_matches_host_func_implementation():
    from library.functions import get_collect_output_path
    from library.functions.host_func import (
        get_collect_output_path as host_func_impl,
    )

    assert get_collect_output_path is host_func_impl
