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

"""Contract tests: the OpenLDAP TLS certificate is verified before use (CD-021).

The certificate under ``auth/tls_certs`` is mounted into ``omnia_auth``,
copied to nodes that pin it, and installed in the OIM trust store. Before any
of that, ``generate_tls_certs.yml`` must confirm that it parses, stays valid,
names the LDAP server IP, and matches its private key.
"""

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROLE = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "orchestrator"
    / "roles"
    / "deploy_openldap"
)
TASKS_FILE = ROLE / "tasks" / "generate_tls_certs.yml"
VARS_FILE = ROLE / "vars" / "main.yml"
VERIFY_TASKS = (
    "Check TLS certificate validity period",
    "Check TLS certificate matches the LDAP server address",
    "Read TLS certificate public key",
    "Read TLS private key public component",
    "Verify TLS certificate before use",
)
SERVER_IP = "10.20.30.40"


def _tasks():
    return yaml.safe_load(TASKS_FILE.read_text(encoding="utf-8"))


def _openssl_cert(directory, name, ip, days=30, key=None):
    key_path = directory / f"{name}.key"
    cert_path = directory / f"{name}.crt"
    argv = ["openssl", "req", "-x509", "-nodes", "-days", str(days)]
    if key is None:
        argv += ["-newkey", "rsa:2048", "-keyout", str(key_path)]
    else:
        argv += ["-key", str(key)]
    argv += ["-out", str(cert_path), "-subj", f"/CN={ip}", "-addext", f"subjectAltName=IP:{ip}"]
    subprocess.run(argv, check=True, capture_output=True, timeout=60)
    return cert_path, key_path


def _run_verify(tmp_path, cert, key, server_ip, min_validity):
    by_name = {task.get("name"): task for task in _tasks()}
    role_vars = yaml.safe_load(VARS_FILE.read_text(encoding="utf-8"))
    play = [
        {
            "hosts": "localhost",
            "gather_facts": False,
            "vars": {
                "auth_certs_dir": str(cert.parent),
                "tls_cert_file": cert.name,
                "tls_key_file": key.name,
                "ldap_server_ip": server_ip,
                "tls_cert_min_validity_seconds": min_validity,
                "tls_cert_invalid_msg": role_vars["tls_cert_invalid_msg"],
            },
            "tasks": [by_name[name] for name in VERIFY_TASKS],
        }
    ]
    playbook = tmp_path / "verify.yml"
    playbook.write_text(yaml.safe_dump(play), encoding="utf-8")
    return subprocess.run(
        ["ansible-playbook", "-i", "localhost,", "-c", "local", str(playbook)],
        capture_output=True,
        text=True,
        timeout=240,
        check=False,
    )


def test_verification_runs_before_trust_store_install():
    names = [task.get("name") for task in _tasks()]
    install = names.index("Install generated TLS certificate in system trust store")
    assert all(names.index(name) < install for name in VERIFY_TASKS)
    assert names.index("Generate self-signed TLS certificate") < names.index(VERIFY_TASKS[0])
    for name in VERIFY_TASKS[:-1]:
        task = next(task for task in _tasks() if task.get("name") == name)
        assert task["ansible.builtin.command"]["argv"][0] == "openssl"


@pytest.mark.skipif(
    shutil.which("ansible-playbook") is None or shutil.which("openssl") is None,
    reason="ansible-playbook or openssl not installed",
)
@pytest.mark.parametrize(
    "case",
    ["valid", "wrong_ip", "key_mismatch", "expiring"],
)
def test_certificate_verification_outcomes(tmp_path, case):
    certs = tmp_path / "certs"
    certs.mkdir()
    cert, key = _openssl_cert(certs, "ldapserver", SERVER_IP)
    server_ip, min_validity = SERVER_IP, 86400
    if case == "wrong_ip":
        server_ip = "10.20.30.41"
    elif case == "key_mismatch":
        _, other_key = _openssl_cert(certs, "other", SERVER_IP)
        other_key.replace(key)
    elif case == "expiring":
        min_validity = 31 * 86400

    result = _run_verify(tmp_path, cert, key, server_ip, min_validity)
    if case == "valid":
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0, result.stdout
        assert "OpenLDAP TLS certificate under auth/tls_certs is unusable" in result.stdout
