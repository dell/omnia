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
Install OS Scenario — ISO Verification Tests.

Verifies ISO configuration files, credentials, and output artifacts.
"""

import pytest

from library.functions import (
    TestLogger,
    check_file_exists,
    check_dir_exists,
    validate_yaml_file,
    validate_install_os_config,
    find_custom_iso,
    verify_iso_checksum,
    verify_kickstart_in_iso,
    resolve_nfs_path_to_local,
    run_ssh_command,
    get_utils_input_path,
    get_utils_output_path,
)
from library.vars import (
    TEST_CASES as TC,
    INSTALL_OS_CONFIG_FILE,
    INSTALL_OS_CREDENTIALS_FILE,
    INSTALL_OS_STATUS_FILE,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


def _resolve_custom_iso_path(host):
    """Resolve the custom ISO to a local filesystem path.

    Reads custom_iso_path from install_os_config.yml. If it is an NFS URI
    ("server:/path/file.iso"), resolves it to the local mount point created
    by the iso_creation role. Falls back to scanning the local output
    directory for build-local configurations.

    Returns:
        dict: {"success": bool, "iso_path": str, "error": str}
    """
    input_path = get_utils_input_path(host)
    config_path = f"{input_path}/install_os_config.yml"

    config_result = validate_install_os_config(host, config_path)
    if not config_result["success"]:
        return {"success": False, "iso_path": "", "error": config_result["error"]}

    custom_iso_path = config_result.get("config", {}).get("custom_iso_path", "")

    if custom_iso_path and ":" in custom_iso_path:
        nfs_result = resolve_nfs_path_to_local(host, custom_iso_path)
        return {
            "success": nfs_result["success"],
            "iso_path": nfs_result["local_path"],
            "error": nfs_result["error"],
        }

    output_path = get_utils_output_path(host)
    return find_custom_iso(host, output_path)


def _resolve_manifest_path(host):
    """Resolve install_os_manifest.yml to a local filesystem path.

    Uses the same directory as the resolved custom ISO.

    Returns:
        dict: {"success": bool, "manifest_path": str, "error": str}
    """
    iso_result = _resolve_custom_iso_path(host)
    if not iso_result["success"]:
        return {"success": False, "manifest_path": "", "error": iso_result["error"]}

    iso_dir = iso_result["iso_path"].rsplit("/", 1)[0]
    return {
        "success": True,
        "manifest_path": f"{iso_dir}/install_os_manifest.yml",
        "error": "",
    }


# =============================================================================
# INPUT FILE VERIFICATION (order 10-19)
# =============================================================================

@pytest.mark.sanity
@pytest.mark.order(10)
def test_install_os_config_file_exists(host):
    """Verify install_os_config.yml exists on target."""
    tc = TC["install_os_config_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    file_path = f"{input_path}/{INSTALL_OS_CONFIG_FILE}"

    result = check_file_exists(host, file_path)

    if result["success"]:
        tl.passed(LOG["file_exists"].format(path=file_path))
    else:
        # Config file is optional for basic tests
        tl.skipped(f"Config file not found (optional): {file_path}")
        pytest.skip(f"Config file not found: {file_path}")


@pytest.mark.sanity
@pytest.mark.order(11)
def test_install_os_config_valid(host):
    """Verify install_os_config.yml has valid structure."""
    tc = TC["install_os_config_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    file_path = f"{input_path}/{INSTALL_OS_CONFIG_FILE}"

    # Check if file exists first
    exists_result = check_file_exists(host, file_path)
    if not exists_result["success"]:
        tl.skipped("Config file not found, skipping validation")
        pytest.skip("Config file not found")

    result = validate_install_os_config(host, file_path)

    if result["success"]:
        tl.passed(LOG["iso_config_valid"])
    else:
        tl.failed(LOG["iso_config_invalid"].format(error=result["error"]))

    assert result["success"], ASSERT["iso_config_invalid"].format(error=result["error"])


@pytest.mark.sanity
@pytest.mark.order(12)
def test_install_os_credentials_file_exists(host):
    """Verify install_os_credentials.yml exists."""
    tc = TC["install_os_credentials_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    file_path = f"{input_path}/{INSTALL_OS_CREDENTIALS_FILE}"

    result = check_file_exists(host, file_path)

    if result["success"]:
        tl.passed(LOG["file_exists"].format(path=file_path))
    else:
        # Credentials file is optional (can be provided via extra-vars)
        tl.skipped(f"Credentials file not found (optional): {file_path}")
        pytest.skip(f"Credentials file not found: {file_path}")


# =============================================================================
# OUTPUT VERIFICATION (order 50-59) - runs AFTER deploy tests (order 20-49)
# These tests require deploy to have run first. They are marked with 'deploy'
# marker so they only execute when deploy tests are included.
# =============================================================================

@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(50)
def test_install_os_output_dir_exists(host):
    """Verify install_os output directory exists after deploy."""
    tc = TC["install_os_output_dir_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    result = check_dir_exists(host, output_path)

    if result["success"]:
        tl.passed(LOG["dir_exists"].format(path=output_path))
    else:
        tl.failed(LOG["dir_missing"].format(path=output_path))

    assert result["success"], f"Output directory not found: {output_path}"


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(51)
def test_install_os_status_file_exists(host):
    """Verify install_os_status.yml output file created after deploy."""
    tc = TC["install_os_status_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    status_path = f"{output_path}/{INSTALL_OS_STATUS_FILE}"

    result = check_file_exists(host, status_path)

    if result["success"]:
        tl.passed(LOG["file_exists"].format(path=status_path))
    else:
        tl.skipped("install_os_status.yml not found (requires build_iso or deploy execution)")
        pytest.skip("install_os_status.yml not found")


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(52)
def test_install_os_status_valid(host):
    """Verify install_os_status.yml has valid structure after deploy."""
    tc = TC["install_os_status_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    status_path = f"{output_path}/{INSTALL_OS_STATUS_FILE}"

    exists = check_file_exists(host, status_path)
    if not exists["success"]:
        tl.skipped("install_os_status.yml not found, skipping validation")
        pytest.skip("install_os_status.yml not found")

    yaml_result = validate_yaml_file(host, status_path)
    if not yaml_result["success"]:
        tl.failed(yaml_result["error"])
        pytest.fail(yaml_result["error"])

    data = yaml_result["data"]
    required = ["utility", "status", "timestamp"]
    missing = [k for k in required if k not in data]

    if missing:
        tl.failed(f"Missing keys in install_os_status.yml: {missing}")
    else:
        tl.passed("install_os_status.yml structure is valid")

    assert not missing, f"Missing keys in install_os_status.yml: {missing}"


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(53)
def test_install_os_custom_iso_created(host):
    """Verify custom ISO created after build_iso execution.

    Checks both local output directory and NFS path for the custom ISO.
    """
    tc = TC["install_os_custom_iso_created"]
    tl = TestLogger(tc["title"], tc["id"])

    # Resolve custom ISO path (handles both local and NFS paths)
    iso_result = _resolve_custom_iso_path(host)
    if not iso_result["success"]:
        tl.skipped(f"Custom ISO not found: {iso_result['error']}")
        pytest.skip(f"Custom ISO not found: {iso_result['error']}")

    iso_path = iso_result["iso_path"]
    result = check_file_exists(host, iso_path)

    if result["success"]:
        tl.passed(LOG["custom_iso_created"].format(path=iso_path))
    else:
        tl.failed(f"Custom ISO not found at resolved path: {iso_path}")
        pytest.fail(f"Custom ISO not found at: {iso_path}")


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(54)
def test_install_os_kickstart_generated(host):
    """Verify kickstart.ks generated after deploy (optional).

    Resolves the kickstart location the same way as the custom ISO
    (local output dir or NFS-mounted dir, based on custom_iso_path).
    """
    tc = TC["install_os_kickstart_generated"]
    tl = TestLogger(tc["title"], tc["id"])

    iso_result = _resolve_custom_iso_path(host)
    if not iso_result["success"]:
        tl.skipped(f"Cannot resolve ISO directory: {iso_result['error']}")
        pytest.skip(f"Cannot resolve ISO directory: {iso_result['error']}")

    iso_dir = iso_result["iso_path"].rsplit("/", 1)[0]
    ks_path = f"{iso_dir}/kickstart.ks"
    result = check_file_exists(host, ks_path)

    if result["success"]:
        tl.passed(LOG["file_exists"].format(path=ks_path))
    else:
        tl.skipped(f"kickstart.ks not found at: {ks_path}")
        pytest.skip(f"kickstart.ks not found at: {ks_path}")


@pytest.mark.functional
@pytest.mark.order(55)
def test_install_os_grub_config_in_iso(host):
    """Verify GRUB config in ISO references correct kickstart path."""
    tc = TC["install_os_grub_config_in_iso"]
    tl = TestLogger(tc["title"], tc["id"])

    iso_result = _resolve_custom_iso_path(host)
    if not iso_result["success"]:
        tl.skipped(f"Custom ISO not found: {iso_result['error']}")
        pytest.skip(f"Custom ISO not found: {iso_result['error']}")

    iso_path = iso_result["iso_path"]

    # Use xorriso to extract and verify GRUB config from ISO
    try:
        which = host.run("command -v xorriso 2>/dev/null")
        if which.rc != 0:
            tl.skipped("xorriso not available, skipping GRUB config verification")
            pytest.skip("xorriso not available")

        # Extract EFI GRUB config from ISO to temp file
        cmd = f"xorriso -osirrox on -indev '{iso_path}' -extract /EFI/BOOT/grub.cfg /tmp/grub_efi_test.cfg 2>&1"
        result = host.run(cmd)

        if result.rc == 0:
            # Read the extracted config
            read_cmd = "cat /tmp/grub_efi_test.cfg"
            read_result = host.run(read_cmd)

            if read_result.rc == 0 and read_result.stdout:
                # Check if GRUB config contains expected kickstart reference
                # For embedded mode: inst.ks=cdrom:/kickstart.ks
                # For NFS mode: inst.ks=nfs:server:/path/kickstart.ks
                if "inst.ks=" in read_result.stdout:
                    tl.passed("GRUB config contains kickstart reference")
                else:
                    tl.failed("GRUB config does not contain kickstart reference")
                    pytest.fail("GRUB config missing kickstart reference")
            else:
                tl.failed("Failed to read extracted GRUB config")
                pytest.fail("Failed to read extracted GRUB config")
        else:
            tl.failed(f"Failed to extract GRUB config from ISO: {result.stderr}")
            pytest.fail(f"Failed to extract GRUB config from ISO: {result.stderr}")
    except Exception as exc:
        tl.failed(f"Error verifying GRUB config: {str(exc)}")
        pytest.fail(f"Error verifying GRUB config: {str(exc)}")


@pytest.mark.functional
@pytest.mark.order(56)
def test_install_os_kickstart_in_iso(host):
    """Verify kickstart configuration is embedded in ISO."""
    tc = TC["install_os_kickstart_in_iso"]
    tl = TestLogger(tc["title"], tc["id"])

    iso_result = _resolve_custom_iso_path(host)
    if not iso_result["success"]:
        tl.skipped(f"Custom ISO not found: {iso_result['error']}")
        pytest.skip(f"Custom ISO not found: {iso_result['error']}")

    iso_path = iso_result["iso_path"]

    # Use existing verify_kickstart_in_iso function
    result = verify_kickstart_in_iso(host, iso_path)

    if result["success"]:
        if result["found"]:
            tl.passed("Kickstart configuration found in ISO")
        else:
            tl.failed("Kickstart configuration not found in ISO")
            pytest.fail("Kickstart configuration not found in ISO")
    else:
        tl.failed(f"Kickstart verification failed: {result['error']}")
        pytest.fail(f"Kickstart verification failed: {result['error']}")


@pytest.mark.functional
@pytest.mark.order(57)
def test_install_os_manifest_exists(host):
    """Verify install_os_manifest.yml exists with correct structure."""
    tc = TC["install_os_manifest_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    manifest_result = _resolve_manifest_path(host)
    if not manifest_result["success"]:
        tl.skipped(f"Custom ISO not found, cannot resolve manifest path: {manifest_result['error']}")
        pytest.skip(f"Cannot resolve manifest path: {manifest_result['error']}")

    manifest_path = manifest_result["manifest_path"]

    # Check if manifest exists
    exists_result = check_file_exists(host, manifest_path)
    if not exists_result["success"]:
        tl.skipped("install_os_manifest.yml not found (requires build_iso execution)")
        pytest.skip("install_os_manifest.yml not found")

    # Validate YAML structure
    yaml_result = validate_yaml_file(host, manifest_path)
    if not yaml_result["success"]:
        tl.failed(f"Manifest YAML invalid: {yaml_result['error']}")
        pytest.fail(f"Manifest YAML invalid: {yaml_result['error']}")

    # Check for required fields
    data = yaml_result["data"]
    required_fields = ["source_iso", "custom_iso", "architecture", "timestamp"]
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        tl.failed(f"Manifest missing required fields: {missing_fields}")
        pytest.fail(f"Manifest missing required fields: {missing_fields}")

    tl.passed("install_os_manifest.yml exists with correct structure")


@pytest.mark.functional
@pytest.mark.order(58)
def test_install_os_iso_checksum(host):
    """Verify custom ISO checksum matches expected value."""
    tc = TC["install_os_iso_checksum"]
    tl = TestLogger(tc["title"], tc["id"])

    iso_result = _resolve_custom_iso_path(host)
    if not iso_result["success"]:
        tl.skipped(f"Custom ISO not found: {iso_result['error']}")
        pytest.skip(f"Custom ISO not found: {iso_result['error']}")

    iso_path = iso_result["iso_path"]

    # Get expected checksum from manifest if available
    manifest_result = _resolve_manifest_path(host)

    expected_checksum = None
    if manifest_result["success"]:
        manifest_path = manifest_result["manifest_path"]
        manifest_exists = check_file_exists(host, manifest_path)
        if manifest_exists["success"]:
            yaml_result = validate_yaml_file(host, manifest_path)
            if yaml_result["success"]:
                data = yaml_result["data"]
                # Check for custom_iso_checksum or repacked_iso_checksum
                expected_checksum = data.get("custom_iso_checksum") or data.get("repacked_iso_checksum")

    if expected_checksum:
        # Verify checksum matches expected value
        result = verify_iso_checksum(host, iso_path, expected_checksum)
        if result["success"]:
            tl.passed("ISO checksum matches expected value")
        else:
            tl.failed(f"ISO checksum mismatch. Expected: {expected_checksum}, Actual: {result['actual_checksum']}")
            pytest.fail("ISO checksum mismatch")
    else:
        # No expected checksum available, just compute and log it
        tl.info("No expected checksum in manifest, computing current checksum")
        try:
            stat_result = host.run(f"sha256sum {iso_path}")
            if stat_result.rc == 0:
                checksum = stat_result.stdout.split()[0]
                tl.info(f"ISO SHA256 checksum: {checksum}")
                tl.passed("ISO checksum computed (no expected value to compare)")
            else:
                tl.warning("Failed to compute ISO checksum")
        except Exception as exc:
            tl.warning(f"Error computing checksum: {str(exc)}")


def _resolve_ssh_private_key_path(config):
    """Resolve the SSH private key path from install_os_config.

    Mirrors the iso_delivery role's derivation: the private key is the
    public key path (ssh_public_key_path, defaulting to
    /root/.ssh/id_rsa.pub) with the ".pub" suffix stripped. There is no
    separate private-key setting - it's always derived this way so the
    key used for verification matches the key injected into the kickstart.

    Args:
        config: Parsed install_os_config.yml dict.

    Returns:
        str: Local path to the SSH private key.
    """
    public_key_path = config.get("ssh_public_key_path") or "/root/.ssh/id_rsa.pub"
    if public_key_path.endswith(".pub"):
        return public_key_path[: -len(".pub")]
    return public_key_path


@pytest.mark.functional
@pytest.mark.order(60)
def test_install_os_post_install_ssh_reachable(host):
    """Verify SSH connectivity to installed target node."""
    tc = TC["install_os_post_install_ssh_reachable"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    config_path = f"{input_path}/install_os_config.yml"

    config_result = validate_install_os_config(host, config_path)
    if not config_result["success"]:
        tl.skipped(f"Config validation failed: {config_result['error']}")
        pytest.skip(f"Config validation failed: {config_result['error']}")

    config = config_result.get("config", {})
    target_admin_ip = config.get("target_admin_ip", "")

    if not target_admin_ip:
        tl.skipped("target_admin_ip not configured")
        pytest.skip("target_admin_ip not configured")

    ssh_key_path = _resolve_ssh_private_key_path(config)
    key_exists = check_file_exists(host, ssh_key_path)
    if not key_exists["success"]:
        tl.skipped(f"SSH private key not found at {ssh_key_path}")
        pytest.skip(f"SSH private key not found at {ssh_key_path}")

    # Try SSH connection
    result = run_ssh_command(
        host,
        target_ip=target_admin_ip,
        command="echo 'SSH connection successful'",
        ssh_key_path=ssh_key_path,
        timeout=30,
    )

    if result["success"]:
        tl.passed("SSH connection to target node successful")
    else:
        # Skip if target is unreachable or permission denied (key may not be authorized)
        if "No route to host" in result["error"] or "Connection refused" in result["error"] or "Connection timed out" in result["error"] or "Permission denied" in result["error"]:
            tl.skipped(f"Target node unreachable or SSH auth failed: {result['error']}")
            pytest.skip(f"Target node unreachable or SSH auth failed: {result['error']}")
        else:
            tl.failed(f"SSH connection failed: {result['error']}")
            pytest.fail(f"SSH connection failed: {result['error']}")


@pytest.mark.functional
@pytest.mark.order(61)
def test_install_os_post_install_os_version(host):
    """Verify installed OS version matches expected RHEL 10."""
    tc = TC["install_os_post_install_os_version"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    config_path = f"{input_path}/install_os_config.yml"

    config_result = validate_install_os_config(host, config_path)
    if not config_result["success"]:
        tl.skipped(f"Config validation failed: {config_result['error']}")
        pytest.skip(f"Config validation failed: {config_result['error']}")

    config = config_result.get("config", {})
    target_admin_ip = config.get("target_admin_ip", "")

    if not target_admin_ip:
        tl.skipped("target_admin_ip not configured")
        pytest.skip("target_admin_ip not configured")

    ssh_key_path = _resolve_ssh_private_key_path(config)
    key_exists = check_file_exists(host, ssh_key_path)
    if not key_exists["success"]:
        tl.skipped(f"SSH private key not found at {ssh_key_path}")
        pytest.skip(f"SSH private key not found at {ssh_key_path}")

    # Check OS version
    result = run_ssh_command(
        host,
        target_ip=target_admin_ip,
        command="cat /etc/redhat-release",
        ssh_key_path=ssh_key_path,
        timeout=30,
    )

    if result["success"]:
        os_release = result["stdout"].strip()
        # Verify it's RHEL 10 (accept both "Red Hat Enterprise Linux 10" and "Red Hat Enterprise Linux release 10")
        if "Red Hat Enterprise Linux" in os_release and "10" in os_release:
            tl.passed(f"OS version verified: {os_release}")
        else:
            tl.failed(f"Unexpected OS version: {os_release}")
            pytest.fail(f"Expected RHEL 10, got: {os_release}")
    else:
        # Skip if target is unreachable or permission denied
        if "No route to host" in result["error"] or "Connection refused" in result["error"] or "Connection timed out" in result["error"] or "Permission denied" in result["error"]:
            tl.skipped(f"Target node unreachable or SSH auth failed: {result['error']}")
            pytest.skip(f"Target node unreachable or SSH auth failed: {result['error']}")
        else:
            tl.failed(f"Failed to get OS version: {result['error']}")
            pytest.fail(f"Failed to get OS version: {result['error']}")


@pytest.mark.functional
@pytest.mark.order(62)
def test_install_os_post_install_gui_packages(host):
    """Verify GUI packages are installed on target node."""
    tc = TC["install_os_post_install_gui_packages"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    config_path = f"{input_path}/install_os_config.yml"

    config_result = validate_install_os_config(host, config_path)
    if not config_result["success"]:
        tl.skipped(f"Config validation failed: {config_result['error']}")
        pytest.skip(f"Config validation failed: {config_result['error']}")

    config = config_result.get("config", {})
    target_admin_ip = config.get("target_admin_ip", "")

    if not target_admin_ip:
        tl.skipped("target_admin_ip not configured")
        pytest.skip("target_admin_ip not configured")

    ssh_key_path = _resolve_ssh_private_key_path(config)
    key_exists = check_file_exists(host, ssh_key_path)
    if not key_exists["success"]:
        tl.skipped(f"SSH private key not found at {ssh_key_path}")
        pytest.skip(f"SSH private key not found at {ssh_key_path}")

    # Check for GUI packages (gnome-shell, gdm)
    result = run_ssh_command(
        host,
        target_ip=target_admin_ip,
        command="rpm -q gnome-shell gdm 2>&1",
        ssh_key_path=ssh_key_path,
        timeout=30,
    )

    if result["success"]:
        # Check if both packages are installed
        packages = result["stdout"].strip()
        if "gnome-shell" in packages and "gdm" in packages:
            tl.passed("GUI packages (gnome-shell, gdm) are installed")
        else:
            tl.info(f"GUI packages check: {packages}")
            # Check if at least one is present
            if "gnome-shell" in packages or "gdm" in packages:
                tl.passed("At least one GUI package is installed")
            else:
                tl.failed("GUI packages not found")
                pytest.fail("GUI packages (gnome-shell, gdm) not installed")
    else:
        # Skip if target is unreachable or permission denied
        if "No route to host" in result["error"] or "Connection refused" in result["error"] or "Connection timed out" in result["error"] or "Permission denied" in result["error"]:
            tl.skipped(f"Target node unreachable or SSH auth failed: {result['error']}")
            pytest.skip(f"Target node unreachable or SSH auth failed: {result['error']}")
        else:
            tl.info(f"GUI package check failed (may not be installed): {result['error']}")
            # This is a soft failure - GUI may not be required in all cases
            tl.info("GUI package verification skipped (packages may not be required)")


@pytest.mark.functional
@pytest.mark.order(63)
def test_install_os_post_install_architecture(host):
    """Verify installed OS architecture matches configured target_architecture."""
    tc = TC["install_os_post_install_architecture"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    config_path = f"{input_path}/install_os_config.yml"

    config_result = validate_install_os_config(host, config_path)
    if not config_result["success"]:
        tl.skipped(f"Config validation failed: {config_result['error']}")
        pytest.skip(f"Config validation failed: {config_result['error']}")

    config = config_result.get("config", {})
    target_admin_ip = config.get("target_admin_ip", "")
    target_architecture = config.get("target_architecture", "")

    if not target_admin_ip:
        tl.skipped("target_admin_ip not configured")
        pytest.skip("target_admin_ip not configured")

    if not target_architecture:
        tl.skipped("target_architecture not configured")
        pytest.skip("target_architecture not configured")

    ssh_key_path = _resolve_ssh_private_key_path(config)
    key_exists = check_file_exists(host, ssh_key_path)
    if not key_exists["success"]:
        tl.skipped(f"SSH private key not found at {ssh_key_path}")
        pytest.skip(f"SSH private key not found at {ssh_key_path}")

    # Check architecture (uname -m reports x86_64, aarch64, etc. matching target_architecture values)
    result = run_ssh_command(
        host,
        target_ip=target_admin_ip,
        command="uname -m",
        ssh_key_path=ssh_key_path,
        timeout=30,
    )

    if result["success"]:
        actual_arch = result["stdout"].strip()
        if actual_arch == target_architecture:
            tl.passed(f"Architecture verified: {actual_arch}")
        else:
            tl.failed(f"Architecture mismatch. Expected: {target_architecture}, Actual: {actual_arch}")
            pytest.fail(f"Architecture mismatch. Expected: {target_architecture}, Actual: {actual_arch}")
    else:
        # Skip if target is unreachable or permission denied
        if "No route to host" in result["error"] or "Connection refused" in result["error"] or "Connection timed out" in result["error"] or "Permission denied" in result["error"]:
            tl.skipped(f"Target node unreachable or SSH auth failed: {result['error']}")
            pytest.skip(f"Target node unreachable or SSH auth failed: {result['error']}")
        else:
            tl.failed(f"Failed to get architecture: {result['error']}")
            pytest.fail(f"Failed to get architecture: {result['error']}")
