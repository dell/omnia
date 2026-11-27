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

"""Which repository hosts are not this OIM: names, addresses, aliases and unresolvable names."""

import time

from library.functions import contract_func as contract

OWN = {"oim.lab.example", "oim", "10.0.0.1"}


def test_own_names_and_addresses_are_this_oim_without_dns(monkeypatch):
    """The OIM's own name or address needs no lookup."""
    monkeypatch.setattr(contract, "_resolve", lambda _host: (_ for _ in ()).throw(AssertionError))
    assert contract.external_hosts({"oim.lab.example", "oim", "10.0.0.1"}, OWN) == set()


def test_alias_that_resolves_to_this_oim_is_local(monkeypatch):
    """A name that resolves to an address of the OIM is this OIM."""
    monkeypatch.setattr(
        contract, "_resolve", lambda host: {"10.0.0.1"} if host == "repo" else set())
    assert contract.external_hosts({"repo"}, OWN) == set()


def test_other_and_unresolvable_hosts_are_external(monkeypatch):
    """Another server and a name that does not resolve are checked, not hidden."""
    monkeypatch.setattr(
        contract, "_resolve", lambda host: {"10.9.9.9"} if host == "other.example" else set())
    assert contract.external_hosts({"other.example", "typo.example", "oim"}, OWN) == {
        "other.example", "typo.example"}


def test_slow_dns_is_cut_off(monkeypatch):
    """A lookup that does not answer in time gives no addresses."""
    monkeypatch.setattr(contract, "_DNS_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(contract.socket, "getaddrinfo", lambda *_args: time.sleep(1))
    started = time.monotonic()
    assert contract._resolve("slow.example") == set()  # pylint: disable=protected-access
    assert time.monotonic() - started < 0.9
