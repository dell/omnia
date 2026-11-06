#!/bin/sh
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

set -e

TLS_CERT=/etc/openldap/certs/ldapserver.crt
TLS_KEY=/etc/openldap/certs/ldapserver.key
TLS_CA_FILE="${LDAP_TLS_CA_FILE:-}"

tls_fail() {
  echo "FATAL: TLS certificate $TLS_CERT verification failed: $*" >&2
  exit 1
}

# --- Validate required bind-mounted files ---
for f in /etc/openldap/slapd.conf /container-init/bootstrap.ldif; do
  if [ ! -f "$f" ]; then
    echo "FATAL: Required file $f not found." \
      "Ensure it is bind-mounted via Quadlet Volume directives." >&2
    exit 1
  fi
done

# --- Initialize data directory (needed when volume is mounted) ---
# Ownership is repaired on every start: databases written while slapd ran as
# root must stay writable once slapd runs as the ldap user.
mkdir -p /var/lib/openldap/openldap-data /run/openldap
chown -R ldap:ldap /var/lib/openldap /run/openldap

# --- Bootstrap LDAP database on first run ---
if [ ! -f /var/lib/openldap/openldap-data/__initialized ]; then
  echo "Bootstrapping LDAP database..."
  slapadd -f /etc/openldap/slapd.conf -l /container-init/bootstrap.ldif
  chown -R ldap:ldap /var/lib/openldap
  touch /var/lib/openldap/openldap-data/__initialized
fi

# --- Verify and install TLS certificate into trust store ---
# Without LDAP_TLS_CA_FILE the certificate must be self-signed (Omnia's
# generated certificate is its own trust anchor). A certificate issued by a
# separate CA must be verified against that CA through LDAP_TLS_CA_FILE.
TRUST_SRC="$TLS_CERT"
TRUST_NAME=ldapserver.crt
if [ -f "$TLS_CERT" ]; then
  command -v openssl >/dev/null 2>&1 || tls_fail "openssl is not available in the image"
  openssl x509 -in "$TLS_CERT" -noout 2>/dev/null || tls_fail "not a valid PEM X.509 certificate"
  openssl x509 -in "$TLS_CERT" -noout -checkend 0 >/dev/null || tls_fail "certificate has expired"

  if [ -n "$TLS_CA_FILE" ]; then
    [ -f "$TLS_CA_FILE" ] || tls_fail "CA file $TLS_CA_FILE not found"
    openssl verify -x509_strict -purpose sslserver -CAfile "$TLS_CA_FILE" "$TLS_CERT" >/dev/null \
      || tls_fail "certificate is not signed by the CA in $TLS_CA_FILE"
    TRUST_SRC="$TLS_CA_FILE"
    TRUST_NAME=ldap-ca.crt
  else
    cert_subject=$(openssl x509 -in "$TLS_CERT" -noout -subject | sed 's/^subject=//')
    cert_issuer=$(openssl x509 -in "$TLS_CERT" -noout -issuer | sed 's/^issuer=//')
    [ "$cert_subject" = "$cert_issuer" ] \
      || tls_fail "certificate is issued by a separate CA ($cert_issuer) and" \
        "LDAP_TLS_CA_FILE is not set; provide the CA certificate under" \
        "/etc/openldap/certs and set LDAP_TLS_CA_FILE"
    openssl verify -check_ss_sig -x509_strict -purpose sslserver \
      -CAfile "$TLS_CERT" "$TLS_CERT" >/dev/null \
      || tls_fail "self-signed certificate signature or purpose check failed"
  fi

  if [ -f "$TLS_KEY" ]; then
    cert_pub=$(openssl x509 -in "$TLS_CERT" -noout -pubkey) \
      || tls_fail "unable to read certificate public key"
    key_pub=$(openssl pkey -in "$TLS_KEY" -pubout) || tls_fail "unable to read private key $TLS_KEY"
    [ "$cert_pub" = "$key_pub" ] || tls_fail "certificate does not match private key $TLS_KEY"
  fi

  if [ -n "${LDAP_TLS_CERT_SHA256:-}" ]; then
    actual_fp=$(openssl x509 -in "$TLS_CERT" -noout -fingerprint -sha256 \
      | cut -d= -f2 | tr -d ':' | tr 'a-f' 'A-F')
    expected_fp=$(printf '%s' "$LDAP_TLS_CERT_SHA256" | tr -d ': ' | tr 'a-f' 'A-F')
    [ "$actual_fp" = "$expected_fp" ] \
      || tls_fail "SHA-256 fingerprint does not match pinned LDAP_TLS_CERT_SHA256"
  fi

  mkdir -p /usr/local/share/ca-certificates
  cp "$TRUST_SRC" "/usr/local/share/ca-certificates/$TRUST_NAME"
  chmod 0644 "/usr/local/share/ca-certificates/$TRUST_NAME"
  if command -v update-ca-certificates >/dev/null 2>&1; then
    update-ca-certificates
  else
    echo "WARNING: update-ca-certificates not available;" \
      "certificate copied but trust store not rebuilt" >&2
  fi
fi

# --- Confirm slapd can read its configuration and TLS material after the drop ---
if command -v su >/dev/null 2>&1; then
  for f in /etc/openldap/slapd.conf "$TLS_KEY" "$TLS_CERT" "$TLS_CA_FILE"; do
    [ -n "$f" ] && [ -f "$f" ] || continue
    su -s /bin/sh ldap -c "test -r '$f'" 2>/dev/null || {
      echo "FATAL: slapd runs as ldap (uid $(id -u ldap), gid $(id -g ldap))" \
        "but cannot read $f. Grant group $(id -g ldap) read access" \
        "(mode 0640) on the host." >&2
      exit 1
    }
  done
fi

# --- Start slapd (sockets are bound as root, then privileges are dropped) ---
exec /usr/sbin/slapd -u ldap -g ldap -f /etc/openldap/slapd.conf -h 'ldap:/// ldaps:///' -d 0
