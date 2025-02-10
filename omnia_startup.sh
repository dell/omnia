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

core_container_status=false
oim_cleanup=false
oim_reset=false
retain_config=false
omnia_path=""
hashed_passwd=""



# This function is responsible for initializing the Omnia core container
# It prompts the user for the Omnia shared path and the root password.
# It checks if the Omnia shared path exists.
#
start_omnia_core() {
    # Initialize the container configuration
    init_container_config

    # Validate the system environment
    validate_oim

    # Setup the container
    setup_container
}


# This function is responsible for cleaning up the Omnia core container.
# It removes the container and performs the necessary cleanup steps.
#
cleanup_omnia_core() {
    # Remove the container
    remove_container

    # Perform the necessary cleanup steps
    cleanup_config
}

cleanup_config(){
    fetch_config
    ssh_key_file="/root/.ssh/oim_rsa"
    # Remove the public key from authorized_keys
    if [ -f "$ssh_key_file.pub" ]; then
        sed -i "\|^$(cat $ssh_key_file.pub)$|d" ~/.ssh/authorized_keys
        echo -e "${GREEN}Public key has been removed from authorized_keys.${NC}"
    else
        echo -e "${RED}Public key file not found.${NC}"
    fi

    # Remove the private key
    if [ -f "$ssh_key_file" ]; then
        rm -f "$ssh_key_file"
        echo -e "${GREEN}Private key has been removed.${NC}"
    else
        echo -e "${RED}Private key file not found.${NC}"
    fi
    ssh-keygen -R "[localhost]:2222" >/dev/null 2>&1
    
    rm -rf $omnia_path/omnia

    echo -e "${GREEN}Omnia core configuration has been cleaned up.${NC}"
}

remove_container() {
    if podman rm -f omnia_core; then
        echo -e "${GREEN}Omnia core container has been removed.${NC}"
    else
        echo -e "${RED}Failed to remove Omnia core container.${NC}"
    fi

    if podman rmi omnia_core; then
        echo -e "${GREEN}Omnia core image has been removed.${NC}"
    else
        echo -e "${RED}Failed to remove Omnia core image.${NC}"
    fi
}

init_container_config() {
    # Print message for the Omnia core container status
    if [ "$core_container_status" = true ]; then
        echo -e "${BLUE}Omnia core container is already running.${NC}"

    else
        echo -e "${BLUE}Omnia core container is not running.${NC}"
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
}

fetch_config() {
    core_config=$(podman exec -ti omnia_core /bin/bash -c 'cat /opt/omnia/.data/oim_metadata.yml')
    readarray -t config_lines <<<"$core_config"
    for line in "${config_lines[@]}"; do
        key=$(echo "$line" | awk -F ':' '{print $1}')
        value=$(echo "$line" | awk -F ':' '{print $2}')
        case $key in
            oim_shared_path)
                omnia_path=$(echo "$value" | tr -d '[:space:]')
                ;;
            omnia_core_hashed_passwd)
                hashed_passwd=$(echo "$value" | tr -d '[:space:]')
                ;;
        esac
    done

    if [ -z "$omnia_path" ] || [ -z "$hashed_passwd" ]; then
        echo -e "${RED}Failed to fetch data from metadata file.${NC}"
        exit 1
    fi

}
validate_oim() {
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
}

setup_container() {
    
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
}


# Check if the omnia_core container is already running
running_containers=$(podman ps -a --format '{{.Names}}' | grep -E 'omnia_core')
if [ -n "$running_containers" ]; then
    core_container_status=true
fi

if [ "$core_container_status" = true ]; then
    echo -e "${GREEN}Omnia core container is already running.${NC}"
    echo -e "${GREEN}Do you want to:${NC}"
    echo -e "${GREEN}1. Cleanup the container.${NC}"
    echo -e "${GREEN}2. Reinstall the container.${NC}"
    read -p "Enter your choice (1 or 2): " choice
    if [ "$choice" = "1" ]; then
        cleanup_omnia_core
    elif [ "$choice" = "2" ]; then
        echo -e "${GREEN} What configuration do you want to use for reinstallation:${NC}"
        echo -e "${GREEN}1. Retain old configuration.${NC}"
        echo -e "${GREEN}2. Overwrite and create new configuration.${NC}"
        read -p "Enter your choice (1 or 2): " choice
        if [ "$choice" = "1" ]; then
            remove_container
            setup_container
        elif [ "$choice" = "2" ]; then
            cleanup_omnia_core
            start_omnia_core

else
    echo -e "${GREEN}Starting Omnia core container.${NC}"
    start_omnia_core
fi