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

# --- Validate required bind-mounted files ---
for f in /etc/openldap/slapd.conf /container-init/bootstrap.ldif; do
  if [ ! -f "$f" ]; then
    echo "FATAL: Required file $f not found. Ensure it is bind-mounted via Quadlet Volume directives." >&2
    exit 1
  fi
done

# --- Initialize data directory (needed when volume is mounted) ---
mkdir -p /var/lib/openldap/openldap-data
chown ldap:ldap /var/lib/openldap/openldap-data

# --- Bootstrap LDAP database on first run ---
if [ ! -f /var/lib/openldap/openldap-data/__initialized ]; then
  echo "Bootstrapping LDAP database..."
  slapadd -f /etc/openldap/slapd.conf -l /container-init/bootstrap.ldif
  chown -R ldap:ldap /var/lib/openldap
  touch /var/lib/openldap/openldap-data/__initialized
fi

# --- Install TLS certificate into trust store ---
if [ -f /etc/openldap/certs/ldapserver.crt ]; then
  cp /etc/openldap/certs/ldapserver.crt /usr/local/share/ca-certificates/ldapserver.crt
  update-ca-certificates
fi

# --- Start slapd, dropping privileges to ldap user ---
exec /usr/sbin/slapd -f /etc/openldap/slapd.conf \
  -u ldap -g ldap -h 'ldap:/// ldaps:///' -d 0
