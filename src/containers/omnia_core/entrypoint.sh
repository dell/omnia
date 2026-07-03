#!/bin/bash

# Call script to copy pulp cert
/cert-copy.sh

# Grab the hashed password
omnia_core_hashed_passwd=$(grep omnia_core_hashed_passwd /opt/omnia/.data/oim_metadata.yml | awk -F: '{print $2}' | tr -d ' ')

echo "root:$omnia_core_hashed_passwd" | chpasswd -e
    
# Start SSH daemon
/usr/sbin/sshd -D
