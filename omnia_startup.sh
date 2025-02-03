#!/bin/bash

# Copyright © 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
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


# This script is used to generate the Omnia core docker image.
# The image is based on Fedora and uses systemd to start all of the necessary
# services.
#
# This script prompts the user for the Omnia shared path and the root
# password. It then checks if the Omnia shared path exists.
#
# The script checks if the ssh key file exists. If it does not exist, a new ssh

# Color Definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color


# Check if the omnia_core container is already running
running_containers=$(podman ps -a --format '{{.Names}}' | grep -E 'omnia_core')
if [ -n "$running_containers" ]; then
    echo -e "${RED}Omnia core container is already running.${NC}"
    exit
fi

# Print prompt for the Omnia shared path
echo -e "${BLUE}Please provide Omnia shared path:${NC}"

echo -e "${BLUE}It is recommended to use a NFS share for Omnia shared path. ${NC}"
echo -e "${BLUE}If you are not using NFS, make sure enough space is available on the disk. ${NC}"

# Prompt the user for the Omnia shared path.
read -p "Enter: " omnia_path

# Check if the Omnia shared path exists.
if [ ! -d "$omnia_path" ]; then
    echo -e "${RED}Omnia shared path does not exist!${NC}"
    exit
fi

# Print prompt for the Omnia core root password
echo -e "${BLUE}Please provide Omnia core root password for accessing container:${NC}"

# Prompt the user for the Omnia core root password.
read -p "Enter: " -s passwd

# Print prompt for the Omnia core root password confirmation
echo -e "\n${BLUE}Please confirm password:${NC}"

# Prompt the user for the Omnia core root password confirmation.
read -s -p "Enter: " cnf_passwd

# Check if the provided passwords match.
if [ "$passwd" != "$cnf_passwd" ]; then
    echo -e "${RED}Invalid Omnia core root password, passwords do not match!${NC}"
    exit 1
fi

# Check if the password contains any of the invalid characters
invalid_chars='[\\|&;`"><*?!$(){}[\]]'
if [[ "$passwd" =~ $invalid_chars ]]; then
    echo -e "${RED}Invalid password, passwords must not contain any of these special characters: [\\|&;\`\"><*?!$(){}[\]]${NC}"
    exit 1
fi

hashed_passwd=$(openssl passwd -1 $passwd)
ssh_key_file="/root/.ssh/oim_rsa"
ssh_port=2222

if [ -f "$ssh_key_file" ]; then
    echo -e "\n${BLUE}Skipping generating new ssh key pair.${NC}"
else
    echo -e "\n${GREEN}Generating a new ssh key pair.${NC}"
    ssh-keygen -t rsa -b 4096 -C "omnia_oim" -q -N '' -f /root/.ssh/oim_rsa
    {
        echo "Host omnia_core"
        echo "    Hostname localhost"
        echo "    Port $ssh_port"
        echo "    User root"
        echo "    IdentityFile ~/.ssh/oim_rsa"
        echo "    IdentitiesOnly yes"
    } >> ~/.ssh/config
fi

# Create the ssh configuration directory if it does not exist.
echo -e "${GREEN}Creating the ssh configuration directory if it does not exist.${NC}"
mkdir -p "$omnia_path/omnia/ssh_config/.ssh"

# Copy the ssh private key to the omnia shared path.
echo -e "${GREEN}Copying the ssh private key to the omnia shared path.${NC}"
cp $ssh_key_file "$omnia_path/omnia/ssh_config/.ssh/id_rsa"

# Copy the ssh public key to the omnia shared path.
echo -e "${GREEN}Copying the ssh public key to the omnia shared path.${NC}"
cp $ssh_key_file.pub "$omnia_path/omnia/ssh_config/.ssh/id_rsa.pub"

# Get the ssh public key.
ssh_public_key="$(cat /root/.ssh/oim_rsa.pub)"


# Add ssh public key to the authorized_keys.
echo -e "${GREEN}Adding ssh public key to the authorized_keys.${NC}"
if grep -q "$ssh_public_key" ~/.ssh/authorized_keys; then
    echo -e "${BLUE}Skipping adding ssh public key to the authorized_keys.${NC}"
else
    echo "$ssh_public_key" >> ~/.ssh/authorized_keys
    chmod 600 ~/.ssh/authorized_keys
fi

# Add ssh public key to the authorized_keys in the ssh_config directory.
echo -e "${GREEN}Adding ssh public key to the authorized_keys in the Omnia ssh_config directory.${NC}"
if [ -f "$omnia_path/omnia/ssh_config/.ssh/authorized_keys" ] && grep -q "$ssh_public_key" "$omnia_path/omnia/ssh_config/.ssh/authorized_keys"; then
    echo -e "${BLUE}Skipping adding ssh public key to the authorized_keys in the Omnia ssh_config directory.${NC}"
else
    echo "$ssh_public_key" >> "$omnia_path/omnia/ssh_config/.ssh/authorized_keys"
    chmod 600 "$omnia_path/omnia/ssh_config/.ssh/authorized_keys"
fi

# Check if the hostname is configured with a domain name.
if hostname -d; then
    echo -e "${BLUE}Hostname is configured with a domain name.${NC}"
else
    echo -e "${RED}Invalid hostname, hostname is not configured with a domain name!${NC}"
    exit 1
fi

podman --version

# Capture the exit status
if [ $? -eq 0 ]; then
    echo -e "${BLUE}Podman is installed. Version: $(podman --version)${NC}"
else
    echo -e "${RED}Podman is not installed.${NC}"
    exit 1
fi

# Enable the podman socket to start at boot
echo -e "${BLUE}Enabling podman.socket...${NC}"
systemctl enable podman.socket

# Start the podman socket now
echo -e "${BLUE}Starting podman.socket...${NC}"
systemctl start podman.socket

# Print a success message after enabling and starting the podman socket
echo -e "${GREEN}Podman socket has been enabled and started.${NC}"

# Print message for pulling the Omnia core docker image.
echo -e "${BLUE}Pulling the Omnia core image.${NC}"

# Pull the Omnia core docker image.
# if podman pull omnia_core:latest; then
#     echo -e "${GREEN}Omnia core image has been pulled.${NC}"
# else
#     echo -e "${RED}Failed to pull Omnia core image.${NC}"
# fi

# Print message for running the Omnia core docker image.
echo -e "${GREEN}Running the Omnia core image.${NC}"
if podman run -dt --hostname omnia_core --restart=always -v $omnia_path/omnia:/opt/omnia:z -v $omnia_path/omnia/ssh_config/.ssh:/root/.ssh:z -e ROOT_PASSWORD_HASH=$hashed_passwd --net=host --name omnia_core --cap-add=CAP_AUDIT_WRITE omnia_core:latest; then
    echo -e "${GREEN}Omnia core image has been started.${NC}"
else
    echo -e "${RED}Failed to start Omnia core image.${NC}"
fi

# Create the input directory if it does not exist.
echo -e "${GREEN}Creating the input directory if it does not exist.${NC}"
mkdir -p "$omnia_path/omnia/input/project_default/"

# Create the default.yml file if it does not exist.
# This file contains the name of the project.
if [ ! -f "$omnia_path/omnia/input/default.yml" ]; then
    echo -e "${BLUE}Creating default.yml file.${NC}"
    {
        echo "project_name: project_default"
    } >> "$omnia_path/omnia/input/default.yml"
fi

# Copy input files from pod to /opt/omnia/project_default/
echo -e "${BLUE}Copying input files from container to project_default folder.${NC}"
podman exec -u root omnia_core sh -c 'for file in /omnia/input/*; do cp -r "$file" /opt/omnia/input/project_default/; done'

# Copy shard libraries from pod to /opt/omnia/shard_libraries/
echo -e "${BLUE}Copying shard libraries from container to shard_libraries folder.${NC}"
podman exec -u root omnia_core cp -r /omnia/shared_libraries/ /opt/omnia/

# Create the .data directory if it does not exist.
# This is where the oim_metadata.yml file is stored.
echo -e "${GREEN}Creating the .data directory if it does not exist.${NC}"
mkdir -p "$omnia_path/omnia/.data"

oim_metadata_file="$omnia_path/omnia/.data/oim_metadata.yml"

if [ ! -f "$oim_metadata_file" ]; then
    echo -e "${GREEN}Creating oim_metadata file${NC}"
    {
        echo "oim_crt: \"podman\""
        echo "oim_shared_path: $omnia_path"
        echo "omnia_version: $omnia_release"
        echo "oim_hostname: $(hostname)"
        echo "omnia_core_hashed_passwd: $hashed_passwd"
    } >> "$oim_metadata_file"
fi

echo -e "${GREEN}
----------------------------------------------------------------------
         Omnia Core image built and running successfully.

         Entering the container:
           Though podman:
           # podman exec -it -u root omnia_core bash
           
           Direct SSH:
           # Passwordless SSH
           # ssh omnia_core

         You are now in the Omnia environment.

----------------------------------------------------------------------
${NC}"

touch ~/.ssh/known_hosts
# Add entry to /root/.ssh/known_hosts file to prevent errors caused by Known host
ssh-keygen -R "[localhost]:2222" >/dev/null 2>&1  # Remove existing entry if it exists
ssh-keyscan -p 2222 localhost 2>/dev/null | grep -v "^#" >> ~/.ssh/known_hosts  # Scan and add the new key

# Waiting for container to be ready
sleep 2

# Entering Omnia-core container
ssh omnia_core
