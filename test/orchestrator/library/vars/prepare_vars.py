# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Immutable contracts for Orchestrator prepare verification."""

OPENCHAMI_CONTAINERS: tuple[str, ...] = (
    "boot-service",
    "coresmd-coredhcp",
    "coresmd-coredns",
    "haproxy",
    "metadata-service",
    "postgres",
    "smd",
    "step-ca",
    "tokensmith",
)

OPENCHAMI_ACTIVE_UNITS: tuple[str, ...] = (
    "openchami.target",
    "acme-deploy.service",
    "acme-register.service",
    "boot-service.service",
    "coresmd-coredhcp.service",
    "coresmd-coredns.service",
    "haproxy.service",
    "metadata-service.service",
    "openchami-cert-trust.service",
    "postgres.service",
    "smd.service",
    "step-ca.service",
    "tokensmith.service",
)

OPENCHAMI_INITIALIZATION_UNIT = "smd-init.service"

OPENCHAMI_DATA_VOLUMES: tuple[str, ...] = (
    "boot-service-data",
    "metadata-service-data",
    "postgres-data",
)

OPENCHAMI_PACKAGES: tuple[str, ...] = ("openchami", "ochami")

OPENCHAMI_CONFIG_ARTIFACTS: tuple[tuple[str, int, str], ...] = (
    ("/etc/ochami/config.yaml", 0o644, "yaml"),
    ("/etc/openchami/configs/boot-service.yaml", 0o644, "yaml"),
    ("/etc/openchami/configs/metadata-service.yaml", 0o644, "yaml"),
    ("/etc/openchami/configs/coredhcp.yaml", 0o644, "yaml"),
    ("/etc/openchami/configs/Corefile", 0o644, "text"),
    ("/etc/openchami/configs/haproxy.cfg", 0o644, "text"),
    ("/etc/openchami/configs/openchami.env", 0o644, "text"),
    ("/etc/openchami/configs/tokensmith.json", 0o644, "json"),
    (
        ("/etc/containers/systemd/tokensmith.container.d/99-site-override.conf"),
        0o644,
        "text",
    ),
)

POSTGRES_INIT_SCRIPT = "/etc/openchami/pg-init/multi-psql-db.sh"
POSTGRES_CONTAINER = "postgres"
POSTGRES_REQUIRED_DATABASE = "hmsds"
POSTGRES_REQUIRED_ROLE = "smd-user"
POSTGRES_READINESS_SCRIPT = (
    'if pg_isready -q -U "$POSTGRES_USER" -d postgres; then '
    'printf "READY|ready\\n"; else '
    'printf "READY|unavailable\\n"; exit 20; fi; '
    'database=$(psql -X -U "$POSTGRES_USER" -d postgres '
    '-v ON_ERROR_STOP=1 -Atqc "SELECT 1 FROM pg_database '
    "WHERE datname = 'hmsds'\") || { "
    'printf "DATABASE|query_failed\\n"; exit 21; }; '
    'if [ "$database" = 1 ]; then printf "DATABASE|present\\n"; '
    'else printf "DATABASE|missing\\n"; exit 22; fi; '
    'role=$(psql -X -U "$POSTGRES_USER" -d postgres '
    '-v ON_ERROR_STOP=1 -Atqc "SELECT 1 FROM pg_roles '
    "WHERE rolname = 'smd-user'\") || { "
    'printf "ROLE|query_failed\\n"; exit 23; }; '
    'if [ "$role" = 1 ]; then printf "ROLE|present\\n"; '
    'else printf "ROLE|missing\\n"; exit 24; fi; '
    'query=$(psql -X -U "$POSTGRES_USER" -d hmsds '
    '-v ON_ERROR_STOP=1 -Atqc "SELECT 1") || { '
    'printf "QUERY|failed\\n"; exit 25; }; '
    'if [ "$query" = 1 ]; then printf "QUERY|passed\\n"; '
    'else printf "QUERY|failed\\n"; exit 26; fi'
)
HAPROXY_CERT_VOLUME = "haproxy-certs"

OPENCHAMI_API_PATHS: tuple[tuple[str, str], ...] = (
    ("SMD", "/hsm/v2/service/ready"),
    ("Boot Service", "/boot-service/nodes"),
    ("Metadata Service", "/metadata-service/health"),
)

FIREWALL_PORTS: tuple[str, ...] = (
    "53/tcp",
    "53/udp",
    "67/udp",
    "68/udp",
    "69/udp",
    "5432/tcp",
    "27778/tcp",
    "27779/tcp",
    "8081/tcp",
    "8443/tcp",
)

PODMAN_TRUSTED_INTERFACES: tuple[str, ...] = (
    "podman0",
    "podman1",
    "podman2",
    "podman3",
    "podman4",
)

DEFAULT_DNS_FORWARDERS: tuple[str, ...] = ("8.8.8.8", "1.1.1.1")

OPENLDAP_CONTAINER = "omnia_auth"
OPENLDAP_SERVICE = "omnia_auth.service"
OPENLDAP_PORTS: tuple[int, ...] = (389, 636)
OPENLDAP_CONFIG_PATH_SUFFIX = "auth/config/slapd.conf"
OPENLDAP_KEY_PATH_SUFFIX = "auth/tls_certs/ldapserver.key"
OPENLDAP_CERT_PATH_SUFFIX = "auth/tls_certs/ldapserver.crt"
OPENLDAP_QUADLET_PATH = "/etc/containers/systemd/omnia_auth.container"

PREPARE_COMMANDS: dict[str, str] = {
    "container_state": ("podman inspect --format '{{.State.Status}}' %s 2>/dev/null"),
    "container_health": (
        "podman inspect --format "
        "'{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "
        "%s 2>/dev/null"
    ),
    "unit_active": "systemctl is-active %s 2>/dev/null",
    "unit_enabled": "systemctl is-enabled %s 2>/dev/null",
    "unit_result": "systemctl show -p Result --value %s 2>/dev/null",
    "volume_exists": "podman volume exists %s",
    "volume_mountpoint": (
        "podman volume inspect --format '{{.Mountpoint}}' %s 2>/dev/null"
    ),
    "pem_count": "find %s -maxdepth 1 -type f -name '*.pem' | wc -l",
    "package_version": "rpm -q %s 2>/dev/null",
    "api_probe_all": (
        "sudo bash -lc '"
        "token=$(gen_access_token 2>/dev/null) || { "
        'printf "TOKEN|generation_failed\\n"; exit 10; }; '
        'test -n "$token" || { '
        'printf "TOKEN|generation_failed\\n"; exit 10; }; '
        'printf "TOKEN|generated\\n"; '
        "refreshed=0; index=0; "
        'for url in "$@"; do '
        "while :; do "
        "code=$(curl -sS --connect-timeout 5 --max-time 15 "
        '-o /dev/null -w "%%{http_code}" '
        '-H "Authorization: Bearer $token" "$url"); '
        "curl_rc=$?; "
        'if [ "$curl_rc" -ne 0 ]; then '
        'printf "PROBE|%%s|transport|%%s\\n" "$index" "$curl_rc"; '
        "break; "
        "fi; "
        'case "$code" in '
        '2??) printf "PROBE|%%s|reachable|%%s\\n" '
        '"$index" "$code"; break ;; '
        "401|403) "
        'if [ "$refreshed" -eq 0 ]; then '
        "token=$(gen_access_token 2>/dev/null) || { "
        'printf "TOKEN|refresh_failed\\n"; exit 11; }; '
        'test -n "$token" || { '
        'printf "TOKEN|refresh_failed\\n"; exit 11; }; '
        'refreshed=1; printf "TOKEN|refreshed\\n"; continue; '
        "fi; "
        'printf "PROBE|%%s|authentication|%%s\\n" '
        '"$index" "$code"; break ;; '
        '*) printf "PROBE|%%s|http|%%s\\n" '
        '"$index" "$code"; break ;; '
        "esac; "
        "done; "
        "index=$((index + 1)); "
        "done' -- %s %s %s"
    ),
    "postgres_readiness": "podman exec postgres sh -c %s",
    "firewall_port": "firewall-cmd --query-port=%s 2>/dev/null",
    "firewall_interface": (
        "firewall-cmd --zone=trusted --query-interface=%s 2>/dev/null"
    ),
    "firewall_masquerade": (
        "firewall-cmd --zone=trusted --query-masquerade 2>/dev/null"
    ),
    "route": "ip route show %s 2>/dev/null",
    "ldap_identity": ("podman exec %s ldapwhoami -x -H ldap://127.0.0.1:389"),
    "ldap_listener": "ss -H -ltn 'sport = :%s' 2>/dev/null",
    "certificate_valid": "openssl x509 -checkend 86400 -noout -in %s",
    "slapd_validate": "podman exec %s slaptest -u -f /etc/openldap/slapd.conf",
}
