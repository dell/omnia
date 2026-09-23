# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Source contracts for protected image-build infrastructure services."""

import importlib.util
import json
from types import SimpleNamespace


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _read(path):
    return path.read_text(encoding="utf-8")


def test_registry_requires_verified_tls_and_authentication(repo_root):
    """The local registry exposes HTTPS with htpasswd authentication."""
    role = repo_root / "src/image_build_manager/roles/deploy_registry"
    quadlet = _read(role / "templates/registry/registry.service.j2")
    tasks = _read(role / "tasks/main.yml")
    build_vars = _read(
        repo_root / "src/image_build_manager/roles/build_os_images/vars/main.yml"
    )

    assert "REGISTRY_HTTP_TLS_CERTIFICATE" in quadlet
    assert "REGISTRY_HTTP_TLS_KEY" in quadlet
    assert "REGISTRY_AUTH=htpasswd" in quadlet
    assert "REGISTRY_AUTH_HTPASSWD_PATH" in quadlet
    assert "--password-stdin" in tasks
    assert "--tls-verify=true" in tasks
    assert "- registry\n      - set\n      - --tls\n      - enabled" in tasks
    assert "REGISTRY_AUTH_FILE" in build_vars
    assert "registry-auth.json" in build_vars


def test_minio_requires_https_and_vault_backed_credentials(repo_root):
    """MinIO uses TLS and has no well-known credential fallback."""
    role = repo_root / "src/image_build_manager/roles/deploy_minio"
    quadlet = _read(role / "templates/minio/minio.service.j2")
    tasks = _read(role / "tasks/main.yml")
    s3cfg = _read(role / "templates/s3/s3cfg.j2")
    schema = json.loads(
        _read(
            repo_root
            / "src/image_build_manager/plugins/module_utils/input_validation/schema"
            / "image_build_credentials.json"
        )
    )

    assert "/certs/public.crt:ro" in quadlet
    assert "/certs/private.key:ro" in quadlet
    assert "--certs-dir /certs" in quadlet
    assert "EnvironmentFile={{ minio_environment_file }}" in quadlet
    assert 'mode: "0600"' in tasks
    assert "https://{{ admin_nic_ip }}" in tasks
    assert "validate_certs: true" in tasks
    assert "use_https = True" in s3cfg
    assert "check_ssl_certificate = True" in s3cfg
    assert "check_ssl_hostname = True" in s3cfg
    assert set(schema["required"]) >= {"s3_access_id", "s3_secret_key"}
    assert "minioadmin" not in tasks.lower()
    assert "dell123" not in tasks.lower()


def test_powerscale_requires_verified_https(repo_root):
    """The external S3 backend cannot downgrade to unverified HTTP."""
    schema = _read(
        repo_root
        / "src/image_build_manager/plugins/module_utils/input_validation/schema"
        / "image_build_config.json"
    )
    runtime_check = _read(
        repo_root
        / "src/image_build_manager/roles/validate_build_runtime/tasks"
        / "powerscale_check.yml"
    )
    s3cfg = _read(
        repo_root
        / "src/image_build_manager/roles/deploy_minio/templates/s3/s3cfg.j2"
    )

    assert '"pattern": "^https://' in schema
    assert "validate_certs: true" in runtime_check
    assert "validate_certs: false" not in runtime_check
    assert "use_https = True" in s3cfg
    assert "check_ssl_certificate = True" in s3cfg
    assert "check_ssl_hostname = True" in s3cfg


def test_service_pki_is_private_and_installed_as_trust_anchor(repo_root):
    """The managed CA protects its key and distributes only public trust."""
    role = repo_root / "src/image_build_manager/roles/configure_service_pki"
    tasks = _read(role / "tasks/main.yml")
    certificate_tasks = _read(role / "tasks/generate_service_certificate.yml")
    handlers = _read(role / "handlers/main.yml")

    assert 'mode: "0700"' in tasks
    assert 'mode: "0600"' in tasks
    assert "omnia-image-build-ca.crt" in _read(role / "vars/main.yml")
    assert "Refresh the OIM CA trust store" in tasks
    assert "update-ca-trust" in handlers
    assert "subjectAltName=" in certificate_tasks
    assert 'mode: "0600"' in certificate_tasks


def test_build_stream_uses_protected_https_minio_configuration(repo_root):
    """Build Stream receives S3 secrets through a root-only environment file."""
    role = repo_root / "src/build_stream/roles/deploy_bsm"
    tasks = _read(role / "tasks/main.yml")
    quadlet = _read(role / "templates/build_stream.j2")
    variables = _read(role / "vars/main.yml")
    initializer = _read(
        repo_root / "src/build_stream/containers/omnia_build_stream/init_s3cfg.sh"
    )

    assert 'mode: "0600"' in tasks
    assert "MINIO_USE_HTTPS=True" in tasks
    assert "EnvironmentFile={{ build_stream_s3_environment_file }}" in quadlet
    assert "build_stream_container_image_build_ca" in quadlet
    assert "build_stream_s3_init_script" in quadlet
    assert "Install hardened Build Stream S3 initializer" in tasks
    assert "omnia-image-build-ca.crt" in variables
    assert 'MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:?' in initializer
    assert "check_ssl_certificate = True" in initializer
    assert "check_ssl_hostname = True" in initializer
    assert "chmod 600" in initializer


def test_image_build_secrets_are_passed_outside_process_arguments(
    repo_root, tmp_path, monkeypatch
):
    """The orchestrator transfers S3 secrets through a restricted child env."""
    module_path = (
        repo_root
        / "src/image_build_manager/plugins/modules/image_build_orchestrator.py"
    )
    orchestrator = _load_module("image_build_orchestrator_security", module_path)
    captured = {}

    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        captured["environment"] = kwargs["env"]
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)
    access_id = "omnia-service-user"
    secret = "sensitive-minio-secret"

    result = orchestrator._run_build(
        "compute",
        "podman run --rm -e S3_ACCESS -e S3_SECRET builder-image",
        str(tmp_path / "build.log"),
        30,
        {"S3_ACCESS": access_id, "S3_SECRET": secret},
    )

    assert result["status"] == "completed"
    assert access_id not in captured["argv"]
    assert secret not in captured["argv"]
    assert captured["environment"]["S3_ACCESS"] == access_id
    assert captured["environment"]["S3_SECRET"] == secret


def test_image_build_orchestrator_rejects_unapproved_environment_keys(
    repo_root, tmp_path, monkeypatch
):
    """Callers cannot use the privileged module as a general env injector."""
    module_path = (
        repo_root
        / "src/image_build_manager/plugins/modules/image_build_orchestrator.py"
    )
    orchestrator = _load_module("image_build_orchestrator_allowlist", module_path)

    def unexpected_run(*_args, **_kwargs):
        raise AssertionError("subprocess must not run for rejected environment keys")

    monkeypatch.setattr(orchestrator.subprocess, "run", unexpected_run)
    result = orchestrator._run_build(
        "compute",
        "podman run builder-image",
        str(tmp_path / "build.log"),
        30,
        {"LD_PRELOAD": "/tmp/untrusted.so"},
    )

    assert result["status"] == "failed"
    assert "Unsupported build environment key" in result["error"]


def test_security_configuration_is_applied_by_upgrade_flows(repo_root):
    """Documented upgrades reuse the hardened idempotent prepare paths."""
    image_upgrade = _read(
        repo_root
        / "src/image_build_manager/playbooks/upgrade"
        / "upgrade_image_build_manager.yml"
    )
    image_prepare = _read(
        repo_root
        / "src/image_build_manager/playbooks/prepare"
        / "prepare_image_build_manager.yml"
    )
    build_stream_upgrade = _read(
        repo_root
        / "src/build_stream/playbooks/upgrade/upgrade_build_stream.yml"
    )
    build_stream_prepare = _read(
        repo_root
        / "src/build_stream/playbooks/prepare/prepare_build_stream.yml"
    )

    assert "../prepare/prepare_image_build_manager.yml" in image_upgrade
    assert "name: configure_service_pki" in image_prepare
    assert image_prepare.count("apply:") >= 7
    assert image_prepare.count("- upgrade") >= 7
    assert "../prepare/prepare_build_stream.yml" in build_stream_upgrade
    assert "name: deploy_bsm" in build_stream_prepare
    assert build_stream_prepare.count("apply:") >= 2
    assert build_stream_prepare.count("- upgrade") >= 2
