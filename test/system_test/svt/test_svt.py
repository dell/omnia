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

"""Every SVT test, generated from library/vars/test_case_vars.py.

One test per TEST_CASES entry ``<theme>_<name>``, marked with its theme and
stage and ordered by its ``order``. ./run_validation.sh svt_<theme> <stage>
selects them with ``-m "<theme> and <stage>"``. Each test runs one FVT step
(run_svt_test). A new theme or test is data only: no test function to write.
"""

import pytest

from library.functions import run_svt_test
from library.vars import TEST_CASES, THEMES


def _theme_of(key: str) -> str:
    """Return the theme of a TEST_CASES key (the longest theme name it starts with)."""
    themes = [theme for theme in THEMES if key.startswith(f"{theme}_")]
    if not themes:
        raise ValueError(f"TEST_CASES key {key!r} starts with no theme of {list(THEMES)}")
    return max(themes, key=len)


CASES = [
    pytest.param(_theme_of(key), key[len(_theme_of(key)) + 1:], id=key,
                 marks=[getattr(pytest.mark, _theme_of(key)), getattr(pytest.mark, case["stage"]),
                        pytest.mark.order(case["order"])])
    for key, case in sorted(TEST_CASES.items(), key=lambda item: item[1]["order"])
]


@pytest.mark.parametrize(("theme", "name"), CASES)
def test_svt(theme: str, name: str) -> None:
    """Run the FVT step of SVT test <theme>_<name> and assert that it passed."""
    run_svt_test(theme, name)
