# OpenLDAP Role

## Overview
Configures OpenLDAP connection parameters for centralized authentication.

## Purpose
- Builds LDAP search base from domain name
- Configures LDAP bind DN and connection parameters
- Sets up LDAP/LDAPS connection type

## Key Tasks
- **Extract Search Base**: Converts domain to LDAP format (e.g., `example.com` → `dc=example,dc=com`)
- **Set Server IP**: Extracts OpenLDAP server IP from configuration
- **Configure Connection**: Sets LDAP or LDAPS connection type
- **Build Bind DN**: Constructs admin bind DN for authentication
