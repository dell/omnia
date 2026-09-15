# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Remote-safe network input and deployed OpenCHAMI configuration tests."""

from ipaddress import ip_address, ip_network
import posixpath
import re

import pytest
import yaml

from library.functions import load_test_config


ADMIN_REQUIRED = {
    "oim_nic_name", "subnet", "netmask_bits", "primary_oim_admin_ip",
    "primary_oim_bmc_ip", "router", "dynamic_range",
}


def _input_path():
    config = load_test_config()
    shared = config.get("shared_path", "/opt/omnia/orchestrator").rstrip("/")
    return posixpath.join(
        shared, "input", config.get("project_name", "project_default")
    )


def _read(host, path):
    remote_file = host.file(path)
    assert remote_file.is_file, f"Required target file is missing: {path}"
    return remote_file.content_string


def _network_spec(host):
    path = posixpath.join(_input_path(), "network_spec.yml")
    try:
        data = yaml.safe_load(_read(host, path))
    except yaml.YAMLError as exc:
        pytest.fail(f"Invalid YAML in {path}: {exc}")
    assert isinstance(data, dict) and isinstance(data.get("Networks"), list)
    return data


def _network_entry(host, key, required=True):
    for entry in _network_spec(host)["Networks"]:
        if isinstance(entry, dict) and key in entry:
            assert isinstance(entry[key], dict), f"{key} must be a mapping"
            return entry[key]
    if required:
        pytest.fail(f"Network specification has no {key}")
    return None


def _range(value):
    parts = value.split("-") if isinstance(value, str) else []
    assert len(parts) == 2, f"Invalid dynamic range: {value}"
    start, end = (ip_address(part.strip()) for part in parts)
    assert start <= end, f"Reversed dynamic range: {value}"
    return start, end


def _network(config):
    return ip_network(f"{config['subnet']}/{int(config['netmask_bits'])}", strict=False)


@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(1)
def test_network_spec_exists(host):
    """ORCH_FVT_NETWORK_V001: network_spec.yml exists on the selected target."""
    assert host.file(posixpath.join(_input_path(), "network_spec.yml")).is_file


@pytest.mark.functional
@pytest.mark.order(2)
def test_network_spec_valid_yaml(host):
    """ORCH_FVT_NETWORK_V002: network_spec.yml is a non-empty Networks mapping."""
    assert _network_spec(host)["Networks"]


@pytest.mark.functional
@pytest.mark.order(3)
def test_admin_network_required_fields(host):
    """ORCH_FVT_NETWORK_V003: admin_network contains every required field."""
    admin = _network_entry(host, "admin_network")
    assert ADMIN_REQUIRED <= set(admin), sorted(ADMIN_REQUIRED - set(admin))


@pytest.mark.functional
@pytest.mark.order(4)
def test_ip_address_format_validation(host):
    """ORCH_FVT_NETWORK_V004: All configured network addresses are valid IPv4 values."""
    admin = _network_entry(host, "admin_network")
    for key in ("subnet", "primary_oim_admin_ip", "router"):
        assert ip_address(admin[key]).version == 4
    if admin.get("primary_oim_bmc_ip"):
        assert ip_address(admin["primary_oim_bmc_ip"]).version == 4


@pytest.mark.functional
@pytest.mark.order(5)
def test_dynamic_range_format_validation(host):
    """ORCH_FVT_NETWORK_V005: Primary DHCP range uses ordered start-end addresses."""
    _range(_network_entry(host, "admin_network")["dynamic_range"])


@pytest.mark.functional
@pytest.mark.order(6)
def test_netmask_bits_validation(host):
    """ORCH_FVT_NETWORK_V006: Every network uses a valid IPv4 prefix length."""
    for entry in _network_spec(host)["Networks"]:
        config = next(iter(entry.values()))
        assert 1 <= int(config["netmask_bits"]) <= 32


@pytest.mark.functional
@pytest.mark.order(7)
def test_additional_subnets_validation(host):
    """ORCH_FVT_NETWORK_V007: Additional DHCP subnets have complete contained ranges."""
    admin = _network_entry(host, "admin_network")
    for index, subnet in enumerate(admin.get("additional_subnets", [])):
        required = {"subnet", "netmask_bits", "router", "dynamic_range"}
        assert required <= set(subnet), f"additional_subnets[{index}]"
        network = _network(subnet)
        start, end = _range(subnet["dynamic_range"])
        assert start in network and end in network
        assert ip_address(subnet["router"]) in network


@pytest.mark.functional
@pytest.mark.order(8)
def test_dns_configuration_validation(host):
    """ORCH_FVT_NETWORK_V008: DNS server entries contain only IPv4 addresses."""
    for entry in _network_spec(host)["Networks"]:
        config = next(iter(entry.values()))
        for address in config.get("dns", []):
            assert ip_address(address).version == 4


@pytest.mark.functional
@pytest.mark.order(9)
def test_ntp_servers_validation(host):
    """ORCH_FVT_NETWORK_V009: NTP servers have supported type and address values."""
    admin = _network_entry(host, "admin_network")
    hostname = re.compile(r"^(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,}$")
    for ntp in admin.get("ntp_servers", []):
        assert set(ntp) >= {"address", "type"}
        assert ntp["type"] in {"server", "pool"}
        try:
            valid_address = ip_address(ntp["address"]).version == 4
        except ValueError:
            valid_address = bool(hostname.fullmatch(ntp["address"]))
        assert valid_address, f"Invalid NTP address: {ntp['address']}"


@pytest.mark.functional
@pytest.mark.order(10)
def test_ib_network_validation(host):
    """ORCH_FVT_NETWORK_V010: Optional InfiniBand network has a valid IPv4 CIDR."""
    ib_network = _network_entry(host, "ib_network", required=False)
    if ib_network is None:
        pytest.skip("No InfiniBand network is configured")
    network = _network(ib_network)
    assert network.version == 4
    for address in ib_network.get("dns", []):
        assert ip_address(address).version == 4


@pytest.mark.sanity
@pytest.mark.order(11)
def test_coredhcp_config_exists(host):
    """ORCH_FVT_NETWORK_V011: Prepared OpenCHAMI deployment has CoreDHCP configuration."""
    coredhcp = host.file("/etc/openchami/configs/coredhcp.yaml")
    assert coredhcp.is_file and coredhcp.size > 0


@pytest.mark.functional
@pytest.mark.order(12)
def test_coredhcp_multi_subnet_rules(host):
    """ORCH_FVT_NETWORK_V012: CoreDHCP contains a relay rule for each additional subnet."""
    admin = _network_entry(host, "admin_network")
    deployed = _read(host, "/etc/openchami/configs/coredhcp.yaml")
    for subnet in admin.get("additional_subnets", []):
        cidr = f"subnet:{subnet['subnet']}/{subnet['netmask_bits']}"
        assert deployed.count(cidr) >= 2, f"Missing Node/BMC rules for {cidr}"


@pytest.mark.functional
@pytest.mark.order(13)
def test_subnet_containment_check(host):
    """ORCH_FVT_NETWORK_V013: OIM, router, and DHCP range stay inside each subnet."""
    admin = _network_entry(host, "admin_network")
    network = _network(admin)
    start, end = _range(admin["dynamic_range"])
    assert start in network and end in network
    assert ip_address(admin["primary_oim_admin_ip"]) in network
    assert ip_address(admin["router"]) in network


@pytest.mark.functional
@pytest.mark.order(14)
def test_static_routes_table_validation(host):
    """ORCH_FVT_NETWORK_V014: Target routing table covers every configured admin subnet."""
    route_output = host.run("ip -4 route show")
    assert route_output.rc == 0, route_output.stderr
    admin = _network_entry(host, "admin_network")
    expected = [_network(admin)] + [
        _network(subnet) for subnet in admin.get("additional_subnets", [])
    ]
    missing = [str(network) for network in expected if str(network) not in route_output.stdout]
    assert not missing, f"Missing target routes: {missing}"


@pytest.mark.functional
@pytest.mark.order(15)
def test_coredhcp_pool_configuration_validation(host):
    """ORCH_FVT_NETWORK_V015: CoreDHCP advertises every configured DHCP range."""
    admin = _network_entry(host, "admin_network")
    deployed = _read(host, "/etc/openchami/configs/coredhcp.yaml")
    for subnet in [admin] + admin.get("additional_subnets", []):
        network = _network(subnet)
        start, end = _range(subnet["dynamic_range"])
        expected = f"subnet_pool={network},{start},{end}"
        assert expected in deployed, f"Missing CoreDHCP pool: {expected}"


@pytest.mark.functional
@pytest.mark.order(16)
def test_network_interface_configuration_validation(host):
    """ORCH_FVT_NETWORK_V016: Configured OIM administration interface exists and is up."""
    interface = _network_entry(host, "admin_network")["oim_nic_name"]
    assert isinstance(interface, str) and re.fullmatch(
        r"[A-Za-z0-9_.:-]+", interface
    ), f"Invalid network interface name: {interface!r}"
    result = host.run(f"ip link show dev {interface}")
    assert result.rc == 0, f"Missing target interface: {interface}"
    assert "state UP" in result.stdout or "LOWER_UP" in result.stdout


@pytest.mark.functional
@pytest.mark.order(17)
def test_dns_forwarder_configuration_validation(host):
    """ORCH_FVT_NETWORK_V017: CoreDNS has a non-empty forwarder configuration."""
    corefile = _read(host, "/etc/openchami/configs/Corefile")
    forward_lines = [
        line.strip() for line in corefile.splitlines()
        if line.strip().startswith("forward . ")
    ]
    assert len(forward_lines) == 1
    assert len(forward_lines[0].split()) > 2


@pytest.mark.sanity
@pytest.mark.order(18)
def test_routing_table_validation(host):
    """ORCH_FVT_NETWORK_V018: Target has a default route and device-backed IPv4 routes."""
    result = host.run("ip -4 route show")
    assert result.rc == 0, result.stderr
    assert "default" in result.stdout
    assert " dev " in f" {result.stdout}"
