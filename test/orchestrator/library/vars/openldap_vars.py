# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Immutable OpenLDAP test metadata and runtime constants."""

LDAP_PROXY_CONTAINER = "omnia_auth"
LDAP_PROXY_SERVICE = "omnia_auth.service"
LDAP_DEFAULT_PORT = 1389
LDAP_READY_RETRIES = 30
LDAP_READY_DELAY_SECONDS = 2


LDAP_PROXY_SLAPD_TEMPLATE = """include        /etc/openldap/schema/core.schema
include        /etc/openldap/schema/cosine.schema
include        /etc/openldap/schema/nis.schema
include        /etc/openldap/schema/inetorgperson.schema

pidfile         /run/openldap/slapd.pid
argsfile        /run/openldap/slapd.args

# Load dynamic backend modules:
modulepath      /usr/lib64/openldap
moduleload      back_ldap.so
moduleload      back_meta.so

###############################################################################
# Meta database definitions
###############################################################################
database        meta
suffix          "{ldap_suffix}"
rootdn          {ldap_rootdn}
rootpw          {ldap_rootpw}

uri             "{ldap_uri}"
suffixmassage   "{ldap_suffixmassage_local}" "{ldap_suffixmassage_remote}"
idassert-bind
 bindmethod=simple
 binddn="{ldap_bind_dn}"
 credentials="{ldap_bind_credentials}"
 flags=override
 mode=none
TLSCACertificateFile    /etc/openldap/certs/ldapserver.crt
TLSCertificateFile      /etc/openldap/certs/ldapserver.crt
TLSCertificateKeyFile   /etc/openldap/certs/ldapserver.key
"""
