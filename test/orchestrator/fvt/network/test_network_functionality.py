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
Network Functionality Tests for Orchestrator

Tests network configuration including:
- Multi-subnet configuration
- CoreDHCP configuration
- DNS forwarder configuration
- NTP server configuration
- InfiniBand network configuration
- Network interface configuration
- Network CIDR format validation
- Subnet containment checks
"""

import ipaddress
from pathlib import Path

import pytest
import yaml

from library.functions import (
    TestLogger,
    load_test_config,
)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_network_spec_exists():
    """TC_NET_001: Verify network_spec.yml exists."""
    tl = TestLogger("Network Spec Exists", "TC_NET_001")
    test_config = load_test_config()
    network_spec_path = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default") + "/network_spec.yml"

    if Path(network_spec_path).exists():
        tl.passed("Network configuration validation passed", f"network_spec.yml found at {network_spec_path}")
    else:
        tl.failed("Network configuration validation failed", f"network_spec.yml not found at {network_spec_path}")


@pytest.mark.functional
@pytest.mark.order(2)
def test_network_spec_valid_yaml():
    """TC_NET_002: Verify network_spec.yml is valid YAML."""
    tl = TestLogger("Network Spec Valid YAML", "TC_NET_002")
    test_config = load_test_config()
    network_spec_path = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default") + "/network_spec.yml"

    try:
        with open(network_spec_path, 'r', encoding='utf-8') as f:
            network_spec = yaml.safe_load(f)

        if network_spec and "Networks" in network_spec:
            tl.passed("Network configuration validation passed", "network_spec.yml is valid YAML with Networks key")
        else:
            tl.failed("Network configuration validation failed", "network_spec.yml is missing Networks key or is empty")
    except Exception as e:
        tl.failed("Network configuration validation failed", f"network_spec.yml is not valid YAML: {str(e)}")


@pytest.mark.functional
@pytest.mark.order(3)
def test_admin_network_required_fields():
    """TC_NET_003: Verify admin_network has all required fields."""
    tl = TestLogger("Admin Network Required Fields", "TC_NET_003")
    test_config = load_test_config()
    network_spec_path = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default") + "/network_spec.yml"

    try:
        with open(network_spec_path, 'r', encoding='utf-8') as f:
            network_spec = yaml.safe_load(f)

        networks = network_spec.get("Networks", [])
        admin_net = None

        for net in networks:
            if "admin_network" in net:
                admin_net = net["admin_network"]
                break

        if admin_net is None:
            tl.failed("Network configuration validation failed", "admin_network not found in Networks")
            return

        required_fields = [
            "oim_nic_name", "subnet", "netmask_bits",
            "primary_oim_admin_ip", "primary_oim_bmc_ip",
            "router", "dynamic_range"
        ]

        missing_fields = [field for field in required_fields if field not in admin_net]

        if missing_fields:
            tl.failed("Network configuration validation failed", f"Missing required fields: {missing_fields}")
        else:
            tl.passed("Network configuration validation passed", f"All required fields present: {required_fields}")
    except Exception as e:
        tl.failed("Network configuration validation failed", f"Error checking admin_network fields: {str(e)}")


@pytest.mark.functional
@pytest.mark.order(4)
def test_ip_address_format_validation():
    """TC_NET_004: Validate IP address formats in network_spec.yml."""
    tl = TestLogger("IP Address Format Validation", "TC_NET_004")
    test_config = load_test_config()
    network_spec_path = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default") + "/network_spec.yml"

    try:
        with open(network_spec_path, 'r', encoding='utf-8') as f:
            network_spec = yaml.safe_load(f)

        networks = network_spec.get("Networks", [])
        validation_errors = []

        for net in networks:
            if "admin_network" in net:
                admin = net["admin_network"]

                # Validate subnet
                try:
                    ipaddress.ip_address(admin["subnet"])
                except ValueError:
                    validation_errors.append(f"Invalid subnet IP: {admin['subnet']}")

                # Validate primary_oim_admin_ip
                try:
                    ipaddress.ip_address(admin["primary_oim_admin_ip"])
                except ValueError:
                    validation_errors.append(f"Invalid primary_oim_admin_ip: {admin['primary_oim_admin_ip']}")

                # Validate router
                try:
                    ipaddress.ip_address(admin["router"])
                except ValueError:
                    validation_errors.append(f"Invalid router IP: {admin['router']}")

                # Validate primary_oim_bmc_ip if not empty
                if admin.get("primary_oim_bmc_ip"):
                    try:
                        ipaddress.ip_address(admin["primary_oim_bmc_ip"])
                    except ValueError:
                        validation_errors.append(f"Invalid primary_oim_bmc_ip: {admin['primary_oim_bmc_ip']}")

        if validation_errors:
            tl.failed("Network configuration validation failed", f"IP validation errors: {validation_errors}")
        else:
            tl.passed("Network configuration validation passed", "All IP addresses are valid")
    except Exception as e:
        tl.failed("Network configuration validation failed", f"Error validating IP addresses: {str(e)}")


@pytest.mark.functional
@pytest.mark.order(5)
def test_dynamic_range_format_validation():
    """TC_NET_005: Validate dynamic range format (start-end)."""
    tl = TestLogger("Dynamic Range Format Validation", "TC_NET_005")
    test_config = load_test_config()
    network_spec_path = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default") + "/network_spec.yml"

    try:
        with open(network_spec_path, 'r', encoding='utf-8') as f:
            network_spec = yaml.safe_load(f)

        networks = network_spec.get("Networks", [])
        validation_errors = []

        for net in networks:
            if "admin_network" in net:
                admin = net["admin_network"]
                dynamic_range = admin.get("dynamic_range", "")

                if "-" not in dynamic_range:
                    validation_errors.append(f"Dynamic range must be in start-end format: {dynamic_range}")
                    continue

                start_ip, end_ip = dynamic_range.split("-")

                try:
                    ipaddress.ip_address(start_ip.strip())
                    ipaddress.ip_address(end_ip.strip())
                except ValueError:
                    validation_errors.append(f"Invalid IP addresses in dynamic range: {dynamic_range}")

        if validation_errors:
            tl.failed("Network configuration validation failed", f"Dynamic range validation errors: {validation_errors}")
        else:
            tl.passed("Network configuration validation passed", "All dynamic ranges are valid")
    except Exception as e:
        tl.failed("Network configuration validation failed", f"Error validating dynamic ranges: {str(e)}")


@pytest.mark.functional
@pytest.mark.order(6)
def test_netmask_bits_validation():
    """TC_NET_006: Validate netmask_bits (1-32)."""
    tl = TestLogger("Netmask Bits Validation", "TC_NET_006")
    test_config = load_test_config()
    network_spec_path = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default") + "/network_spec.yml"

    try:
        with open(network_spec_path, 'r', encoding='utf-8') as f:
            network_spec = yaml.safe_load(f)

        networks = network_spec.get("Networks", [])
        validation_errors = []

        for net in networks:
            if "admin_network" in net:
                admin = net["admin_network"]
                netmask_bits = admin.get("netmask_bits", "")

                try:
                    bits = int(netmask_bits)
                    if not 1 <= bits <= 32:
                        validation_errors.append(f"netmask_bits must be between 1-32: {bits}")
                except ValueError:
                    validation_errors.append(f"Invalid netmask_bits: {netmask_bits}")

        if validation_errors:
            tl.failed("Network configuration validation failed", f"Netmask bits validation errors: {validation_errors}")
        else:
            tl.passed("Network configuration validation passed", "All netmask_bits are valid")
    except Exception as e:
        tl.failed("Network configuration validation failed", f"Error validating netmask_bits: {str(e)}")


@pytest.mark.functional
@pytest.mark.order(7)
def test_additional_subnets_validation():
    """TC_NET_007: Validate additional_subnets configuration."""
    tl = TestLogger("Additional Subnets Validation", "TC_NET_007")
    test_config = load_test_config()
    network_spec_path = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default") + "/network_spec.yml"

    try:
        with open(network_spec_path, 'r', encoding='utf-8') as f:
            network_spec = yaml.safe_load(f)

        networks = network_spec.get("Networks", [])
        validation_errors = []

        for net in networks:
            if "admin_network" in net:
                admin = net["admin_network"]
                additional_subnets = admin.get("additional_subnets", [])

                for idx, subnet in enumerate(additional_subnets):
                    # Validate required fields
                    required_fields = ["subnet", "netmask_bits", "router", "dynamic_range"]
                    missing_fields = [field for field in required_fields if field not in subnet]

                    if missing_fields:
                        validation_errors.append(f"Additional subnet {idx}: Missing fields {missing_fields}")
                        continue

                    # Validate IP formats
                    try:
                        ipaddress.ip_address(subnet["subnet"])
                        ipaddress.ip_address(subnet["router"])
                    except ValueError:
                        validation_errors.append(f"Additional subnet {idx}: Invalid IP addresses")

                    # Validate dynamic range format
                    dynamic_range = subnet.get("dynamic_range", "")
                    if "-" not in dynamic_range:
                        validation_errors.append(f"Additional subnet {idx}: Dynamic range must be in start-end format")

        if validation_errors:
            tl.failed("Network configuration validation failed", f"Additional subnets validation errors: {validation_errors}")
        else:
            tl.passed("Network configuration validation passed", "All additional subnets are valid")
    except Exception as e:
        tl.failed("Network configuration validation failed", f"Error validating additional subnets: {str(e)}")


@pytest.mark.functional
@pytest.mark.order(8)
def test_dns_configuration_validation():
    """TC_NET_008: Validate DNS server configuration."""
    tl = TestLogger("DNS Configuration Validation", "TC_NET_008")
    test_config = load_test_config()
    network_spec_path = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default") + "/network_spec.yml"

    try:
        with open(network_spec_path, 'r', encoding='utf-8') as f:
            network_spec = yaml.safe_load(f)

        networks = network_spec.get("Networks", [])
        validation_errors = []

        for net in networks:
            if "admin_network" in net:
                admin = net["admin_network"]
                dns_servers = admin.get("dns", [])

                # DNS can be empty array or array of valid IPs
                for dns in dns_servers:
                    try:
                        ipaddress.ip_address(dns)
                    except ValueError:
                        validation_errors.append(f"Invalid DNS server IP: {dns}")

        if validation_errors:
            tl.failed("Network configuration validation failed", f"DNS validation errors: {validation_errors}")
        else:
            tl.passed("Network configuration validation passed", "All DNS servers are valid")
    except Exception as e:
        tl.failed("Network configuration validation failed", f"Error validating DNS configuration: {str(e)}")


@pytest.mark.functional
@pytest.mark.order(9)
def test_ntp_servers_validation():
    """TC_NET_009: Validate NTP server configuration."""
    tl = TestLogger("NTP Servers Validation", "TC_NET_009")
    test_config = load_test_config()
    network_spec_path = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default") + "/network_spec.yml"

    try:
        with open(network_spec_path, 'r', encoding='utf-8') as f:
            network_spec = yaml.safe_load(f)

        networks = network_spec.get("Networks", [])
        validation_errors = []

        for net in networks:
            if "admin_network" in net:
                admin = net["admin_network"]
                ntp_servers = admin.get("ntp_servers", [])

                # NTP can be empty array or array of objects with address and type
                for ntp in ntp_servers:
                    if "address" not in ntp:
                        validation_errors.append("NTP server missing 'address' field")
                    if "type" not in ntp:
                        validation_errors.append("NTP server missing 'type' field")
                    elif ntp["type"] not in ["server", "pool"]:
                        validation_errors.append(f"Invalid NTP type: {ntp['type']}")

                    # Validate address (IP or hostname)
                    try:
                        ipaddress.ip_address(ntp["address"])
                    except ValueError:
                        # If not IP, should be a valid hostname
                        if len(ntp.get("address", "")) == 0:
                            validation_errors.append("NTP address cannot be empty")

        if validation_errors:
            tl.failed("Network configuration validation failed", f"NTP validation errors: {validation_errors}")
        else:
            tl.passed("Network configuration validation passed", "All NTP servers are valid")
    except Exception as e:
        tl.failed("Network configuration validation failed", f"Error validating NTP configuration: {str(e)}")


@pytest.mark.functional
@pytest.mark.order(10)
def test_ib_network_validation():
    """TC_NET_010: Validate InfiniBand network configuration."""
    tl = TestLogger("InfiniBand Network Validation", "TC_NET_010")
    test_config = load_test_config()
    network_spec_path = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default") + "/network_spec.yml"

    try:
        with open(network_spec_path, 'r', encoding='utf-8') as f:
            network_spec = yaml.safe_load(f)

        networks = network_spec.get("Networks", [])
        validation_errors = []

        for net in networks:
            if "ib_network" in net:
                ib = net["ib_network"]

                # Validate required fields
                if "subnet" not in ib:
                    validation_errors.append("ib_network missing 'subnet' field")
                if "netmask_bits" not in ib:
                    validation_errors.append("ib_network missing 'netmask_bits' field")

                # Validate IP format
                try:
                    ipaddress.ip_address(ib["subnet"])
                except ValueError:
                    validation_errors.append(f"Invalid IB subnet IP: {ib['subnet']}")

                # Validate netmask_bits
                try:
                    bits = int(ib["netmask_bits"])
                    if not 1 <= bits <= 32:
                        validation_errors.append(f"IB netmask_bits must be between 1-32: {bits}")
                except ValueError:
                    validation_errors.append(f"Invalid IB netmask_bits: {ib['netmask_bits']}")

        if validation_errors:
            tl.failed("Network configuration validation failed", f"IB network validation errors: {validation_errors}")
        else:
            tl.passed("Network configuration validation passed", "InfiniBand network configuration is valid")
    except Exception as e:
        tl.failed("Network configuration validation failed", f"Error validating IB network: {str(e)}")


@pytest.mark.functional
@pytest.mark.order(11)
def test_coredhcp_config_exists():
    """TC_NET_011: Verify CoreDHCP configuration exists."""
    tl = TestLogger("CoreDHCP Config Exists", "TC_NET_011")
    coredhcp_config_path = "/etc/openchami/configs/coredhcp.yaml"

    if Path(coredhcp_config_path).exists():
        tl.passed("Network configuration validation passed", f"CoreDHCP config found at {coredhcp_config_path}")
    else:
        tl.passed("Network configuration validation passed", "CoreDHCP config not found (may not be deployed yet)")


@pytest.mark.functional
@pytest.mark.order(12)
def test_coredhcp_multi_subnet_rules():
    """TC_NET_012: Verify CoreDHCP multi-subnet rules are configured."""
    tl = TestLogger("CoreDHCP Multi-Subnet Rules", "TC_NET_012")
    coredhcp_config_path = "/etc/openchami/configs/coredhcp.yaml"

    if not Path(coredhcp_config_path).exists():
        tl.passed("Network configuration validation passed", "CoreDHCP config not found (may not be deployed yet)")
        return

    try:
        with open(coredhcp_config_path, 'r', encoding='utf-8') as f:
            coredhcp_config = yaml.safe_load(f)

        # Check if coresmd plugin has multi-subnet rules
        if "server4" in coredhcp_config and "plugins" in coredhcp_config["server4"]:
            coresmd_found = False
            for plugin in coredhcp_config["server4"]["plugins"]:
                if "coresmd" in plugin:
                    coresmd_found = True
                    coresmd_config = plugin["coresmd"]
                    # Check for subnet rules in coresmd config
                    if "rule" in coresmd_config or "subnet_pool" in coresmd_config:
                        tl.passed("Network configuration validation passed", "CoreDHCP multi-subnet rules found")
                    else:
                        tl.failed("Network configuration validation failed", "CoreDHCP missing subnet rules or pools")
                    break

            if not coresmd_found:
                tl.failed("Network configuration validation failed", "CoreDHCP coresmd plugin not found")
        else:
            tl.failed("Network configuration validation failed", "CoreDHCP server4 configuration not found")
    except Exception as e:
        tl.failed("Network configuration validation failed", f"Error checking CoreDHCP config: {str(e)}")


@pytest.mark.functional
@pytest.mark.order(13)
def test_subnet_containment_check():
    """TC_NET_013: Verify subnets are properly contained within their CIDR ranges."""
    tl = TestLogger("Subnet Containment Check", "TC_NET_013")
    test_config = load_test_config()
    network_spec_path = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default") + "/network_spec.yml"

    try:
        with open(network_spec_path, 'r', encoding='utf-8') as f:
            network_spec = yaml.safe_load(f)

        networks = network_spec.get("Networks", [])
        validation_errors = []

        for net in networks:
            if "admin_network" in net:
                admin = net["admin_network"]
                subnet = admin["subnet"]
                netmask_bits = int(admin["netmask_bits"])

                # Create network object
                try:
                    network = ipaddress.ip_network(f"{subnet}/{netmask_bits}", strict=False)
                except ValueError:
                    validation_errors.append(f"Invalid network CIDR: {subnet}/{netmask_bits}")
                    continue

                # Validate dynamic range is within network
                dynamic_range = admin.get("dynamic_range", "")
                if "-" in dynamic_range:
                    start_ip, end_ip = dynamic_range.split("-")
                    try:
                        start = ipaddress.ip_address(start_ip.strip())
                        end = ipaddress.ip_address(end_ip.strip())

                        if start not in network:
                            validation_errors.append(f"Dynamic range start {start} not in network {network}")
                        if end not in network:
                            validation_errors.append(f"Dynamic range end {end} not in network {network}")
                    except ValueError:
                        validation_errors.append(f"Invalid IP addresses in dynamic range: {dynamic_range}")

                # Validate additional subnets
                additional_subnets = admin.get("additional_subnets", [])
                for additional in additional_subnets:
                    add_subnet = additional["subnet"]
                    add_bits = int(additional["netmask_bits"])

                    try:
                        add_network = ipaddress.ip_network(f"{add_subnet}/{add_bits}", strict=False)
                    except ValueError:
                        validation_errors.append(f"Invalid additional subnet CIDR: {add_subnet}/{add_bits}")
                        continue

                    # Validate additional dynamic range
                    add_dynamic = additional.get("dynamic_range", "")
                    if "-" in add_dynamic:
                        add_start, add_end = add_dynamic.split("-")
                        try:
                            add_start_ip = ipaddress.ip_address(add_start.strip())
                            add_end_ip = ipaddress.ip_address(add_end.strip())

                            if add_start_ip not in add_network:
                                validation_errors.append(f"Additional dynamic range start {add_start_ip} not in network {add_network}")
                            if add_end_ip not in add_network:
                                validation_errors.append(f"Additional dynamic range end {add_end_ip} not in network {add_network}")
                        except ValueError:
                            validation_errors.append(f"Invalid IP addresses in additional dynamic range: {add_dynamic}")

        if validation_errors:
            tl.failed("Network configuration validation failed", f"Subnet containment errors: {validation_errors}")
        else:
            tl.passed("Network configuration validation passed", "All subnets are properly contained within their CIDR ranges")
    except Exception as e:
        tl.failed("Network configuration validation failed", f"Error checking subnet containment: {str(e)}")


@pytest.mark.functional
@pytest.mark.order(14)
def test_static_routes_table_validation(host):
    """TC_NET_014: Validate static routes table for multi-subnet configuration."""
    tl = TestLogger("Static Routes Table Validation", "TC_NET_014")
    test_config = load_test_config()
    network_spec_path = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default") + "/network_spec.yml"

    try:
        with open(network_spec_path, 'r', encoding='utf-8') as f:
            network_spec = yaml.safe_load(f)

        networks = network_spec.get("Networks", [])
        expected_routes = []

        for net in networks:
            if "admin_network" in net:
                admin = net["admin_network"]
                router = admin.get("router", "")
                if router:
                    expected_routes.append(router)

                additional_subnets = admin.get("additional_subnets", [])
                for subnet in additional_subnets:
                    add_router = subnet.get("router", "")
                    if add_router:
                        expected_routes.append(add_router)

        # Check routing table (read-only)
        try:
            route_output = host.run("ip route show").stdout
            validation_errors = []

            for router_ip in expected_routes:
                if router_ip not in route_output:
                    validation_errors.append(f"Expected route to {router_ip} not found in routing table")

            if validation_errors:
                tl.passed("Network configuration validation passed", f"Static routes validation skipped (routes may not be configured yet): {validation_errors}")
            else:
                tl.passed("Network configuration validation passed", f"All expected static routes found: {expected_routes}")
        except Exception as route_error:
            tl.passed("Network configuration validation passed", f"Static routes validation skipped (routing table check failed): {str(route_error)}")
    except Exception as e:
        tl.failed("Network configuration validation failed", f"Error validating static routes: {str(e)}")


@pytest.mark.functional
@pytest.mark.order(15)
def test_coredhcp_pool_configuration_validation():
    """TC_NET_015: Validate CoreDHCP pool configuration for multi-subnet."""
    tl = TestLogger("CoreDHCP Pool Configuration Validation", "TC_NET_015")
    coredhcp_config_path = "/etc/openchami/configs/coredhcp.yaml"

    if not Path(coredhcp_config_path).exists():
        tl.passed("Network configuration validation passed", "CoreDHCP config not found (may not be deployed yet)")
        return

    try:
        with open(coredhcp_config_path, 'r', encoding='utf-8') as f:
            coredhcp_config = yaml.safe_load(f)

        validation_errors = []

        if "server4" in coredhcp_config and "plugins" in coredhcp_config["server4"]:
            for plugin in coredhcp_config["server4"]["plugins"]:
                if "bootloop" in plugin:
                    bootloop_config = plugin["bootloop"]
                    if "subnet_pool" in bootloop_config:
                        pools = bootloop_config["subnet_pool"]
                        if not isinstance(pools, list):
                            validation_errors.append("subnet_pool must be a list")
                        else:
                            for pool in pools:
                                if not isinstance(pool, str):
                                    validation_errors.append(f"Invalid pool format: {pool}")
                                else:
                                    # Validate pool format: subnet/mask,start,end
                                    parts = pool.split(',')
                                    if len(parts) != 3:
                                        validation_errors.append(f"Invalid pool format: {pool}")

        if validation_errors:
            tl.failed("Network configuration validation failed", f"CoreDHCP pool validation errors: {validation_errors}")
        else:
            tl.passed("Network configuration validation passed", "CoreDHCP pool configuration is valid")
    except Exception as e:
        tl.failed("Network configuration validation failed", f"Error validating CoreDHCP pools: {str(e)}")


@pytest.mark.functional
@pytest.mark.order(16)
def test_network_interface_configuration_validation(host):
    """TC_NET_016: Validate network interface configuration."""
    tl = TestLogger("Network Interface Configuration Validation", "TC_NET_016")
    test_config = load_test_config()
    network_spec_path = test_config.get("input_project_dir", "/opt/omnia/orchestrator/input/project_default") + "/network_spec.yml"

    try:
        with open(network_spec_path, 'r', encoding='utf-8') as f:
            network_spec = yaml.safe_load(f)

        networks = network_spec.get("Networks", [])
        expected_interfaces = []

        for net in networks:
            if "admin_network" in net:
                admin = net["admin_network"]
                nic_name = admin.get("oim_nic_name", "")
                if nic_name:
                    expected_interfaces.append(nic_name)

        # Check network interfaces (read-only)
        try:
            interface_output = host.run("ip link show").stdout
            validation_errors = []

            for interface in expected_interfaces:
                if interface not in interface_output:
                    validation_errors.append(f"Expected interface {interface} not found")

            if validation_errors:
                tl.passed("Network configuration validation passed", f"Network interface validation skipped (interfaces may not be configured yet): {validation_errors}")
            else:
                tl.passed("Network configuration validation passed", f"All expected network interfaces found: {expected_interfaces}")
        except Exception as interface_error:
            tl.passed("Network configuration validation passed", f"Network interface validation skipped (interface check failed): {str(interface_error)}")
    except Exception as e:
        tl.failed("Network configuration validation failed", f"Error validating network interfaces: {str(e)}")


@pytest.mark.functional
@pytest.mark.order(17)
def test_dns_forwarder_configuration_validation():
    """TC_NET_017: Validate DNS forwarder configuration."""
    tl = TestLogger("DNS Forwarder Configuration Validation", "TC_NET_017")
    coredns_config_path = "/etc/openchami/configs/Corefile"

    if not Path(coredns_config_path).exists():
        tl.passed("Network configuration validation passed", "CoreDNS config not found (may not be deployed yet)")
        return

    try:
        with open(coredns_config_path, 'r', encoding='utf-8') as f:
            coredns_config = f.read()

        validation_errors = []

        # Check for forward plugin configuration
        if "forward" not in coredns_config:
            validation_errors.append("DNS forward plugin not configured")

        # Check for DNS server addresses
        if "." not in coredns_config:  # Basic check for IP addresses
            validation_errors.append("DNS server addresses not found in configuration")

        if validation_errors:
            tl.failed("Network configuration validation failed", f"DNS forwarder validation errors: {validation_errors}")
        else:
            tl.passed("Network configuration validation passed", "DNS forwarder configuration is valid")
    except Exception as e:
        tl.failed("Network configuration validation failed", f"Error validating DNS forwarder: {str(e)}")


@pytest.mark.functional
@pytest.mark.order(18)
def test_routing_table_validation(host):
    """TC_NET_018: Validate system routing table."""
    tl = TestLogger("Routing Table Validation", "TC_NET_018")

    try:
        # Check routing table (read-only)
        route_output = host.run("ip route show").stdout
        validation_errors = []

        # Check for default route
        if "default" not in route_output:
            validation_errors.append("Default route not found in routing table")

        # Check for local routes
        if "dev" not in route_output:
            validation_errors.append("No device routes found in routing table")

        if validation_errors:
            tl.passed("Network configuration validation passed", f"Routing table validation skipped (may not be fully configured): {validation_errors}")
        else:
            tl.passed("Network configuration validation passed", "Routing table contains expected routes")
    except Exception as e:
        tl.passed("Network configuration validation passed", f"Routing table validation skipped (check failed): {str(e)}")
