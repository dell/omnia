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

"""Unit tests for OME OData pagination in ome_server_inventory.OMEClient.

Tests cover:
  - Small inventories that fit in a single page
  - Large inventories (8 000 devices) requiring many pages
  - @odata.count missing → ValueError
  - Retry on transient 5xx errors
  - Page size clamping (>1000, <1)
  - Empty inventory (0 devices)
  - device_type filtering via get_all_devices
"""

import json
import math
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub out ansible.module_utils so we can import ome_server_inventory
# without an Ansible installation.
# ---------------------------------------------------------------------------
_ansible_stub = types.ModuleType("ansible")
_ansible_mu = types.ModuleType("ansible.module_utils")
_ansible_basic = types.ModuleType("ansible.module_utils.basic")
_ansible_basic.AnsibleModule = MagicMock  # type: ignore[attr-defined]
_ansible_stub.module_utils = _ansible_mu  # type: ignore[attr-defined]
_ansible_mu.basic = _ansible_basic  # type: ignore[attr-defined]
sys.modules.setdefault("ansible", _ansible_stub)
sys.modules.setdefault("ansible.module_utils", _ansible_mu)
sys.modules.setdefault("ansible.module_utils.basic", _ansible_basic)

# Now we can safely import the module under test
from ome_server_inventory import OMEClient  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_device(device_id, device_type=1000):
    """Return a minimal device dict as OME would."""
    return {"Id": device_id, "Type": device_type, "Identifier": f"SVC{device_id}"}


def _make_page_response(devices, total_count, status_code=200):
    """Build a mock ``requests.Response`` for one OData page."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = {
        "@odata.count": total_count,
        "value": devices,
    }
    return resp


def _build_paginated_side_effect(all_devices, page_size, total_count=None):
    """Return a side_effect callable that serves pages from *all_devices*.

    Each call to the side_effect pops one page of *page_size* items.
    """
    if total_count is None:
        total_count = len(all_devices)
    remaining = list(all_devices)

    def _side_effect(_method, _url, **_kwargs):
        page = remaining[:page_size]
        del remaining[:page_size]
        return _make_page_response(page, total_count)

    return _side_effect


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPageSizeClamping:
    """page_size should be clamped to [1, 1000]."""

    def test_page_size_default(self):
        client = OMEClient("10.0.0.1", "u", "p")
        assert client.page_size == 200

    def test_page_size_custom(self):
        client = OMEClient("10.0.0.1", "u", "p", page_size=500)
        assert client.page_size == 500

    def test_page_size_clamped_high(self):
        client = OMEClient("10.0.0.1", "u", "p", page_size=5000)
        assert client.page_size == 1000

    def test_page_size_clamped_low(self):
        client = OMEClient("10.0.0.1", "u", "p", page_size=0)
        assert client.page_size == 1

    def test_page_size_negative(self):
        client = OMEClient("10.0.0.1", "u", "p", page_size=-10)
        assert client.page_size == 1


class TestGetPaginatedSmallInventory:
    """Inventory fits in a single page (<= page_size)."""

    def test_single_page(self):
        client = OMEClient("10.0.0.1", "u", "p", page_size=200)
        devices = [_make_device(i) for i in range(5)]
        client._request_with_retry = MagicMock(
            side_effect=_build_paginated_side_effect(devices, 200)
        )

        result, stats = client.get_paginated("https://10.0.0.1/api/DeviceService/Devices")

        assert len(result) == 5
        assert result == devices
        # Only one HTTP call expected
        assert client._request_with_retry.call_count == 1
        assert stats["total_devices_in_ome"] == 5
        assert stats["page_size"] == 200
        assert stats["total_pages"] == 1
        assert stats["pages_fetched"] == 1
        assert stats["devices_retrieved"] == 5

    def test_exact_one_page(self):
        """Exactly page_size items → one full page then an empty second page check."""
        page_size = 3
        client = OMEClient("10.0.0.1", "u", "p", page_size=page_size)
        devices = [_make_device(i) for i in range(page_size)]

        # First call returns full page, count == page_size → accumulated == total → stop
        client._request_with_retry = MagicMock(
            side_effect=_build_paginated_side_effect(devices, page_size)
        )

        result, stats = client.get_paginated("https://10.0.0.1/api/DeviceService/Devices")

        assert len(result) == page_size
        assert stats["pages_fetched"] == 1


class TestGetPaginatedLargeInventory:
    """Simulate a large-scale environment (8 000 devices)."""

    def test_8k_devices(self):
        total = 8000
        page_size = 200
        client = OMEClient("10.0.0.1", "u", "p", page_size=page_size)
        all_devices = [_make_device(i) for i in range(total)]

        client._request_with_retry = MagicMock(
            side_effect=_build_paginated_side_effect(all_devices, page_size)
        )

        result, stats = client.get_paginated("https://10.0.0.1/api/DeviceService/Devices")

        assert len(result) == total
        expected_calls = math.ceil(total / page_size)
        assert client._request_with_retry.call_count == expected_calls
        assert stats["total_devices_in_ome"] == total
        assert stats["page_size"] == page_size
        assert stats["total_pages"] == expected_calls
        assert stats["pages_fetched"] == expected_calls
        assert stats["devices_retrieved"] == total

    def test_20k_devices(self):
        total = 20000
        page_size = 500
        client = OMEClient("10.0.0.1", "u", "p", page_size=page_size)
        all_devices = [_make_device(i) for i in range(total)]

        client._request_with_retry = MagicMock(
            side_effect=_build_paginated_side_effect(all_devices, page_size)
        )

        result, stats = client.get_paginated("https://10.0.0.1/api/DeviceService/Devices")

        assert len(result) == total
        expected_calls = math.ceil(total / page_size)
        assert client._request_with_retry.call_count == expected_calls
        assert stats["total_devices_in_ome"] == total
        assert stats["pages_fetched"] == expected_calls


class TestGetPaginatedEmptyInventory:
    """Zero devices in OME."""

    def test_empty(self):
        client = OMEClient("10.0.0.1", "u", "p", page_size=200)
        client._request_with_retry = MagicMock(
            return_value=_make_page_response([], 0)
        )

        result, stats = client.get_paginated("https://10.0.0.1/api/DeviceService/Devices")

        assert result == []
        assert client._request_with_retry.call_count == 1
        assert stats["total_devices_in_ome"] == 0
        assert stats["devices_retrieved"] == 0
        assert stats["pages_fetched"] == 1


class TestGetPaginatedMissingOdataCount:
    """@odata.count missing from first response → must fail fast."""

    def test_missing_count_raises(self):
        client = OMEClient("10.0.0.1", "u", "p", page_size=200)
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"value": [_make_device(1)]}  # no @odata.count
        client._request_with_retry = MagicMock(return_value=resp)

        with pytest.raises(ValueError, match="@odata.count"):
            client.get_paginated("https://10.0.0.1/api/DeviceService/Devices")


class TestGetPaginatedNon200:
    """Non-200 response on first page → return empty list."""

    def test_404_returns_empty(self):
        client = OMEClient("10.0.0.1", "u", "p", page_size=200)
        resp = MagicMock()
        resp.status_code = 404
        client._request_with_retry = MagicMock(return_value=resp)

        result, stats = client.get_paginated("https://10.0.0.1/api/DeviceService/Devices")
        assert result == []
        assert stats["total_devices_in_ome"] == 0
        assert stats["pages_fetched"] == 0


class TestGetPaginatedURLConstruction:
    """Verify $top and $skip are appended correctly."""

    def test_url_params_first_page(self):
        client = OMEClient("10.0.0.1", "u", "p", page_size=100)
        client._request_with_retry = MagicMock(
            return_value=_make_page_response([], 0)
        )

        _, _ = client.get_paginated("https://10.0.0.1/api/DeviceService/Devices")

        called_url = client._request_with_retry.call_args[0][1]
        assert "$top=100" in called_url
        assert "$skip=0" in called_url

    def test_url_with_existing_query_params(self):
        """When the base URL already has ?filter=..., use & instead of ?."""
        client = OMEClient("10.0.0.1", "u", "p", page_size=50)
        client._request_with_retry = MagicMock(
            return_value=_make_page_response([], 0)
        )

        _, _ = client.get_paginated("https://10.0.0.1/api/DeviceService/Devices?$filter=Type eq 1000")

        called_url = client._request_with_retry.call_args[0][1]
        assert "?$filter=Type eq 1000&$top=50&$skip=0" in called_url


class TestRequestWithRetry:
    """_request_with_retry retries on 5xx and transient errors."""

    @patch("time.sleep", return_value=None)  # skip real delays
    def test_retry_on_500(self, _mock_sleep):
        client = OMEClient("10.0.0.1", "u", "p")
        fail_resp = MagicMock()
        fail_resp.status_code = 503
        ok_resp = MagicMock()
        ok_resp.status_code = 200

        client.session.request = MagicMock(side_effect=[fail_resp, ok_resp])
        result = client._request_with_retry("GET", "https://10.0.0.1/test")

        assert result.status_code == 200
        assert client.session.request.call_count == 2

    @patch("time.sleep", return_value=None)
    def test_retry_exhausted_returns_last_5xx(self, _mock_sleep):
        client = OMEClient("10.0.0.1", "u", "p")
        fail_resp = MagicMock()
        fail_resp.status_code = 500

        client.session.request = MagicMock(return_value=fail_resp)
        result = client._request_with_retry("GET", "https://10.0.0.1/test")

        assert result.status_code == 500
        assert client.session.request.call_count == client.MAX_RETRIES

    @patch("time.sleep", return_value=None)
    def test_retry_on_connection_error(self, _mock_sleep):
        import requests as req

        client = OMEClient("10.0.0.1", "u", "p")
        ok_resp = MagicMock()
        ok_resp.status_code = 200

        client.session.request = MagicMock(
            side_effect=[req.exceptions.ConnectionError("conn refused"), ok_resp]
        )
        result = client._request_with_retry("GET", "https://10.0.0.1/test")
        assert result.status_code == 200

    @patch("time.sleep", return_value=None)
    def test_retry_exhausted_raises_on_timeout(self, _mock_sleep):
        import requests as req

        client = OMEClient("10.0.0.1", "u", "p")
        client.session.request = MagicMock(
            side_effect=req.exceptions.Timeout("timed out")
        )
        with pytest.raises(req.exceptions.Timeout):
            client._request_with_retry("GET", "https://10.0.0.1/test")


class TestGetAllDevices:
    """get_all_devices delegates to get_paginated and applies type filter."""

    def test_type_filter(self):
        client = OMEClient("10.0.0.1", "u", "p", page_size=100)
        mixed = [_make_device(1, 1000), _make_device(2, 2000), _make_device(3, 1000)]
        client._request_with_retry = MagicMock(
            side_effect=_build_paginated_side_effect(mixed, 100)
        )

        result, stats = client.get_all_devices(device_type=1000)
        assert len(result) == 2
        assert all(d["Type"] == 1000 for d in result)
        assert stats["devices_after_type_filter"] == 2
        assert stats["device_type_filter"] == 1000
        assert stats["devices_retrieved"] == 3

    def test_no_type_filter(self):
        client = OMEClient("10.0.0.1", "u", "p", page_size=100)
        mixed = [_make_device(1, 1000), _make_device(2, 2000)]
        client._request_with_retry = MagicMock(
            side_effect=_build_paginated_side_effect(mixed, 100)
        )

        result, stats = client.get_all_devices(device_type=None)
        assert len(result) == 2
        assert "devices_after_type_filter" not in stats
