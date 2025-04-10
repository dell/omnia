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
YELLOW='\033[0;33m'
omnia_release=2.0.0.0

core_container_status=false
omnia_path=""
hashed_passwd=""

# This function is responsible for initializing the Omnia core container
# It prompts the user for the Omnia shared path and the root password.
# It checks if the Omnia shared path exists.
setup_omnia_core() {

    # Initialize the container configuration
    init_container_config

    # Validate the system environment
    validate_oim

    # Setup the container
    setup_container

    # Post container setup configuration
    post_setup_config

    # Start the container
    start_container_session
}


# This function is responsible for cleaning up the Omnia core container.
# It removes the container and performs the necessary cleanup steps.
cleanup_omnia_core() {

    echo -e "${RED} WARNING: This will remove Omnia core container and all files in Omnia Shared Path.${NC}"
    echo -e "${GREEN} You can abort and take backup if you want.${NC}"
    read -p " Are you sure you want to continue with the cleanup? (y/n): " confirm
    if [ "$confirm" = "n" ] || [ "$confirm" = "N" ]; then
        echo -e "${GREEN}Aborting.${NC}"
        exit 0
    elif [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then

        # Fetch the configuration from the Omnia core container.
        fetch_config

        # Remove the container
        remove_container

        # Perform the necessary cleanup steps
        cleanup_config
    fi
}


# This function is responsible for cleaning up the Omnia core container configuration.
# It removes the public key from the authorized_keys file.
# It removes the private key.
# It removes the ssh key from the known_hosts file.
# It removes the Omnia core configuration.
#
cleanup_config(){

    # Set the path to the ssh public key.
    ssh_key_file="$HOME/.ssh/oim_rsa.pub"

    # Remove the public key from the authorized_keys file.
    if [ -f "$ssh_key_file" ]; then
        # Remove the line from the authorized_keys file.
        sed -i "\|^$(cat $ssh_key_file)$|d" $HOME/.ssh/authorized_keys
        echo -e "${GREEN} Public key has been removed from authorized_keys.${NC}"
    else
        echo -e "${RED} Public key file not found.${NC}"
    fi

    # Remove the SSH key pair.
    ssh_key_file="$HOME/.ssh/oim_rsa"
    ssh_key_file_pub="${ssh_key_file}.pub"
    if [ -f "$ssh_key_file" ] && [ -f "$ssh_key_file_pub" ]; then
        rm -f "$ssh_key_file" "$ssh_key_file_pub"
        echo -e "${GREEN} SSH key pair have been removed.${NC}"
    else
        echo -e "${RED} SSH key file not found.${NC}"
    fi

    # Remove the ssh key from the known_hosts file.
    echo -e "${BLUE} Removing ssh key from known_hosts file.${NC}"
    ssh-keygen -R "[localhost]:2222" >/dev/null 2>&1


    # Remove the host entry from the config file in .ssh folder.
    ssh_config_file="$HOME/.ssh/config"
    if [ -f "$ssh_config_file" ]; then
        sed -i '/Host omnia_core/,+5d' "$ssh_config_file"
        echo -e "${GREEN} Host entry has been removed from config file.${NC}"
    else
        echo -e "${RED} Config file not found.${NC}"
    fi

    # Remove the Omnia core configuration.
    echo -e "${BLUE} Removing Omnia core configuration.${NC}"
    rm -rf $omnia_path/omnia/{hosts,input,log,offline_repo,omnia_inventory,pulp,provision,kubespray,pcs,services,shared_libraries,ssh_config,tmp,images,.data}

    # Unmount the NFS shared path if the share option is NFS.
    if [ "$share_option" = "NFS" ]; then
        umount "$omnia_path"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN} NFS shared path has been unmounted.${NC}"
        else
            echo -e "${RED} Failed to unmount NFS shared path.${NC}"
        fi
        # Remove the entry from /etc/fstab
        fstab_file="/etc/fstab"
        if [ -f "$fstab_file" ]; then
            # Create a backup of the fstab file.
            cp "$fstab_file" "$fstab_file.bak"

            # Remove the line from the fstab file.
             sed -i "\#$omnia_path#d" "$fstab_file"
             if [ $? -ne 0 ]; then
                echo -e "${RED} Failed to remove the entry from /etc/fstab.${NC}"
            fi
        fi
    fi

    echo -e "${GREEN} Omnia core configuration has been cleaned up.${NC}"
}

# This function is responsible for removing the Omnia core container.
#
# It removes the container using the 'podman rm -f' command.
# If the container is removed successfully, it prints a success message.
# Otherwise, it prints an error message.
remove_container() {

    # Remove the container.
    echo -e "${BLUE} Removing the Omnia core container.${NC}"
    if podman rm -f omnia_core; then
        echo -e "${GREEN} Omnia core container has been removed.${NC}"
    else
        echo -e "${RED} Failed to remove Omnia core container.${NC}"
    fi

    # Remove the container image.
    # if podman rmi omnia_core; then
    #     echo -e "${GREEN} Omnia core image has been removed.${NC}"
    # else
    #     echo -e "${RED} Failed to remove Omnia core image.${NC}"
    # fi
}


# This function is responsible for initializing the Omnia core container.
#
# It prompts the user for the Omnia shared path and the root
# password. It then checks if the Omnia shared path exists.
#
# The function generates the ssh key pair and copies the private
# key to the Omnia shared path.
#
# The function also copies the ssh public key to the
# authorized_keys file.
#
# The function creates the necessary log directories.
init_container_config() {


    share_option=""

    # Prompt the user to choose the type of Omnia shared path
    echo -e "${BLUE} Please choose the type of Omnia shared path in Omnia Infrastructure Manager (OIM) :${NC}"
    echo -e "${BLUE} It is recommended to use a NFS share for Omnia shared path. ${NC}"
    echo -e "${BLUE} If you are not using NFS, make sure enough space is available on the disk. ${NC}"
    echo -e "${YELLOW} Using a NFS share is mandatory for Omnia shared path if you are planning to have a high availability in OIM or require hierarchical cluster.${NC}"

    # Display the choices for the user
    echo -e "${BLUE} Choose the type of Omnia shared path:${NC}"
    options=( "NFS (recommended)" "Local"  )

    PS3="Select the option number: "

    select opt in "${options[@]}"; do
        case $opt in
            "NFS (recommended)")
                share_option="NFS"
                break
                ;;
            "Local")
                share_option="Local"
                break
                ;;
            *)
                echo -e "${RED} Invalid option.${NC}"
                continue
        esac
    done

    case $share_option in
        "Local")
            # Prompt the user for the Omnia shared path.
            echo -e "${BLUE} Please provide Omnia shared path:${NC}"
            read -p "Omnia shared path: " omnia_path

            # Check if the Omnia shared path exists.
            if [ ! -d "$omnia_path" ]; then
                echo -e "${RED} Omnia shared path does not exist!${NC}"
                exit
            fi
            ;;
        "NFS")
            # Prompt the user for the NFS server IP.
            echo -e "${BLUE} Please provide the NFS server IP:${NC}"
            read -p "NFS server IP: " nfs_server_ip

            # Prompt the user for the NFS server share path.
            echo -e "${BLUE} Please provide the NFS server share path:${NC}"
            read -p "NFS server share path: " nfs_server_share_path

            # Prompt the user for the Omnia share path.
            echo -e "${BLUE} Please provide the Omnia share path:${NC}"
            read -p "Omnia share path: " omnia_path
            ;;
    esac

    # Prompt the user for the Omnia core root password.
    echo -e "${BLUE} Please provide Omnia core root password for accessing container:${NC}"

    read -p " Enter: " -s passwd

    # Prompt the user for the Omnia core root password confirmation.
    echo -e "\n${BLUE} Please confirm password:${NC}"
    read -s -p " Enter: " cnf_passwd

    # Check if the provided passwords match.
    if [ "$passwd" != "$cnf_passwd" ]; then
        echo -e "${RED} Invalid Omnia core root password, passwords do not match!${NC}"
        exit 1
    fi

    # Check if the password contains any of the invalid characters
    invalid_chars='[\\|&;`"><*?!$(){}[\]]'
    if [[ "$passwd" =~ $invalid_chars ]]; then
        echo -e "${RED} Invalid password, passwords must not contain any of these special characters: [\\|&;\`\"><*?!$(){}[\]]${NC}"
        exit 1
    fi

    # Install NFS client package if option NFS is selected
    if [[ "$share_option" == "NFS" ]]; then
        # Install NFS client package
        echo -e "${BLUE} Installing NFS client package.${NC}"
        dnf install -y nfs-utils nfs4-acl-tools

        # Create omnia_path directory if it does not exist
        echo -e "${BLUE} Creating omnia shared path directory if it does not exist.${NC}"
        mkdir -p $omnia_path

        # Validate if NFS server is reachable
        echo -e "${BLUE} Validating if NFS server is reachable.${NC}"
        ping -c1 -W1 $nfs_server_ip > /dev/null
        if [ $? -ne 0 ]; then
            echo -e "${RED} NFS server $nfs_server_ip is not reachable.${NC}"
            exit 1
        fi

        # Mount NFS server share path in Omnia share path
        echo -e "${BLUE} Mounting NFS server share path in Omnia share path.${NC}"
        mount -t nfs -o nosuid,rw,sync,hard,intr,timeo=30 $nfs_server_ip:$nfs_server_share_path $omnia_path

        # Validate if NFS server share path is mounted
        echo -e "${BLUE} Validating if NFS server share path is mounted.${NC}"
        if grep -qs "$nfs_server_ip:$nfs_server_share_path" /proc/mounts; then
            echo -e "${GREEN} NFS server share path is mounted.${NC}"
        else
            echo -e "${RED} NFS server share path is not mounted. Provide valid NFS server details. ${NC}"
            exit 1
        fi

        # Add NFS server share to /etc/fstab to mount on startup
        echo "$nfs_server_ip:$nfs_server_share_path $omnia_path nfs nosuid,rw,sync,hard,intr" >> /etc/fstab
    fi

    hashed_passwd=$(openssl passwd -1 $passwd)
    ssh_key_file="/root/.ssh/oim_rsa"
    ssh_port=2222

    # Generate a new ssh key pair.
    if [ -f "$ssh_key_file" ]; then
        echo -e "\n${BLUE} Skipping generating new ssh key pair.${NC}"
    else
        echo -e "\n${GREEN} Generating a new ssh key pair.${NC}"
        ssh-keygen -t rsa -b 4096 -C "omnia_oim" -q -N '' -f /root/.ssh/oim_rsa
        {
            echo "Host omnia_core"
            echo "    Hostname localhost"
            echo "    Port $ssh_port"
            echo "    User root"
            echo "    IdentityFile ~/.ssh/oim_rsa"
            echo "    IdentitiesOnly yes"
        } >> $HOME/.ssh/config
    fi

    # Create the ssh configuration directory if it does not exist.
    echo -e "${GREEN} Creating the ssh configuration directory if it does not exist.${NC}"
    mkdir -p "$omnia_path/omnia/ssh_config/.ssh"

    # Copy the ssh private key to the omnia shared path.
    echo -e "${GREEN} Copying the ssh private key to the omnia shared path.${NC}"
    cp $ssh_key_file "$omnia_path/omnia/ssh_config/.ssh/id_rsa"

    # Copy the ssh public key to the omnia shared path.
    echo -e "${GREEN} Copying the ssh public key to the omnia shared path.${NC}"
    cp $ssh_key_file.pub "$omnia_path/omnia/ssh_config/.ssh/id_rsa.pub"

    # Get the ssh public key.
    ssh_public_key="$(cat /root/.ssh/oim_rsa.pub)"


    # Add ssh public key to the authorized_keys.
    echo -e "${GREEN} Adding ssh public key to the authorized_keys.${NC}"
    if grep -q "$ssh_public_key" $HOME/.ssh/authorized_keys; then
        echo -e "${BLUE} Skipping adding ssh public key to the authorized_keys.${NC}"
    else
        echo "$ssh_public_key" >> $HOME/.ssh/authorized_keys
        chmod 600 $HOME/.ssh/authorized_keys
    fi

    # Add ssh public key to the authorized_keys in the ssh_config directory.
    echo -e "${GREEN} Adding ssh public key to the authorized_keys in the Omnia ssh_config directory.${NC}"
    if [ -f "$omnia_path/omnia/ssh_config/.ssh/authorized_keys" ] && grep -q "$ssh_public_key" "$omnia_path/omnia/ssh_config/.ssh/authorized_keys"; then
        echo -e "${BLUE} Skipping adding ssh public key to the authorized_keys in the Omnia ssh_config directory.${NC}"
    else
        echo "$ssh_public_key" >> "$omnia_path/omnia/ssh_config/.ssh/authorized_keys"
        chmod 600 "$omnia_path/omnia/ssh_config/.ssh/authorized_keys"
    fi

    # Create the log directory if it does not exist.
    echo -e "${GREEN} Creating the log directory if it does not exist.${NC}"
    mkdir -p "$omnia_path/omnia/log/core/container"
    mkdir -p "$omnia_path/omnia/log/core/playbooks"

    # Create the hosts file for cluster in $omnia_path/omnia/hosts
    echo -e "${GREEN} Creating the hosts file for cluster.${NC}"
    touch "$omnia_path/omnia/hosts"

    # Create the pulp_ha directory if it does not exist.
    echo -e "${GREEN} Creating the pulp HA directory if it does not exist.${NC}"
    mkdir -p "$omnia_path/omnia/pulp/pulp_ha"
}


# This function is responsible for fetching the configuration from the Omnia core.
# It uses podman exec to run a command in the Omnia core container.
# The command retrieves the metadata from the oim_metadata.yml file.
# The metadata is then parsed and the required configuration is extracted.
fetch_config() {

    # Fetch the metadata from the oim_metadata.yml file.
    echo -e "${GREEN} Fetching the metadata from the oim_metadata.yml file.${NC}"
        core_config=$(podman exec -ti omnia_core /bin/bash -c 'cat /opt/omnia/.data/oim_metadata.yml')

    # Split the metadata into separate lines.
    IFS=$'\n' read -r -d '' -a config_lines <<<"$core_config"

    # Loop through the lines and extract the required configuration.
    for line in "${config_lines[@]}"; do
        # Extract the key and value from the line.
        key=$(echo "$line" | awk -F ':' '{print $1}')
        value=$(echo "$line" | awk -F ':' '{print $2}')

        # Check the key and assign the value to the corresponding variable.
        case $key in
            oim_shared_path)
                # Assign the shared path.
                omnia_path=$(echo "$value" | tr -d '[:space:]')
                ;;
            omnia_core_hashed_passwd)
                # Assign the hashed password.
                hashed_passwd=$(echo "$value" | tr -d '[:space:]')
                ;;
            nfs_server_ip)
                # Assign the nfs server ip.
                nfs_server_ip=$(echo "$value" | tr -d '[:space:]')
                ;;
            nfs_server_share_path)
                # Assign the nfs server share path.
                nfs_server_share_path=$(echo "$value" | tr -d '[:space:]')
                ;;
            omnia_share_option)
                # Assign the share option.
                share_option=$(echo "$value" | tr -d '[:space:]')
                ;;
        esac
    done
    # Check if the required configuration is extracted successfully.
    if [ -z "$omnia_path" ] || [ -z "$hashed_passwd" ]; then
        echo -e "${RED} Failed to fetch data from metadata file.${NC}"
        exit 1
    else
        echo -e "${GREEN} Successfully fetched data from metadata file.${NC}"
    fi
}

# Validates the OIM (Omnia Infrastructure Manager) by checking if the hostname is
# configured with a domain name, checking if Podman is installed, enabling and
# starting the Podman socket.
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
        echo -e "${BLUE} Podman is installed. Version: $(podman --version)${NC}"
    else
        echo -e "${RED} Podman is not installed.${NC}"
        exit 1
    fi

    # Enable the podman socket to start at boot
    echo -e "${BLUE} Enabling podman.socket...${NC}"
    systemctl enable podman.socket

    # Start the podman socket now
    echo -e "${BLUE} Starting podman.socket...${NC}"
    systemctl start podman.socket

    # Print a success message after enabling and starting the podman socket
    echo -e "${GREEN} Podman socket has been enabled and started.${NC}"
}

# Sets up the Omnia core container.
# This function pulls the Omnia core Docker image and runs the container.
# It defines the container options and runs the container.
setup_container() {

    # Print message for pulling the Omnia core docker image.
    echo -e "${BLUE} Pulling the Omnia core image.${NC}"

    # Pull the Omnia core docker image.
    # if podman pull omnia_core:latest; then
    #     echo -e "${GREEN} Omnia core image has been pulled.${NC}"
    # else
    #     echo -e "${RED} Failed to pull Omnia core image.${NC}"
    # fi

    # Run the Omnia core container.
    echo -e "${GREEN} Running the Omnia core container.${NC}"

    selinux_option=":z"

    if [ "$share_option" = "NFS" ]; then
        selinux_option=""
    fi

    # Define the container options.
    OPTIONS="-d --restart=always"
    OPTIONS+=" --hostname omnia_core"
    OPTIONS+=" -v $omnia_path/omnia:/opt/omnia$selinux_option"
    OPTIONS+=" -v $omnia_path/omnia/ssh_config/.ssh:/root/.ssh$selinux_option"
    OPTIONS+=" -v $omnia_path/omnia/log/core/container:/var/log$selinux_option"
    OPTIONS+=" -v $omnia_path/omnia/hosts:/etc/hosts$selinux_option"
    OPTIONS+=" -v $omnia_path/omnia/pulp/pulp_ha:/root/.config/pulp$selinux_option"
    OPTIONS+=" -e ROOT_PASSWORD_HASH=$hashed_passwd"
    OPTIONS+=" --net=host"
    OPTIONS+=" --name omnia_core"
    OPTIONS+=" --cap-add=CAP_AUDIT_WRITE"

    # Run the container.
    if podman run $OPTIONS omnia_core:latest; then
        echo -e "${GREEN} Omnia core container has been started.${NC}"
    else
        echo -e "${RED} Failed to start Omnia core container.${NC}"
        echo -e "${RED} Make sure the Omnia core image is present.${NC}"
        exit 1
    fi
}

# This function sets up the configuration for the Omnia core.
#  post_setup_config is a function that sets up the configuration for the Omnia core.
#  It creates the necessary directories and files, copies input files from the Omnia container,
#  and creates the oim_metadata.yml file.
post_setup_config() {

    # Create the ansible tmp directory if it does not exist.
    mkdir -p "$omnia_path/omnia/tmp/.ansible/tmp"
    chmod 757 "$omnia_path/omnia/tmp/.ansible/tmp"
    # Create the input directory if it does not exist.
    echo -e "${GREEN} Creating the input directory if it does not exist.${NC}"
    mkdir -p "$omnia_path/omnia/input/"

    # Create the default.yml file if it does not exist.
    # This file contains the name of the project.
    if [ ! -f "$omnia_path/omnia/input/default.yml" ]; then
        echo -e "${BLUE} Creating default.yml file.${NC}"
        {
            echo "# This file defines the project name."
            echo "# The name of the project should be set in a directory under input."
            echo "project_name: project_default"
        } >> "$omnia_path/omnia/input/default.yml"
    fi

    # Copy input files from /omnia to /opt/omnia/project_default/ inside omnia_core container
    podman exec -u root omnia_core bash -c "cd /omnia && git pull"
    echo -e "${BLUE} Moving input files from /omnia dir to project_default folder.${NC}"
    podman exec -u root omnia_core bash -c "
    mkdir -p /opt/omnia/input/project_default
    cp -r /omnia/input/* /opt/omnia/input/project_default
    rm -rf /omnia/input"

    # Copy shared libraries from /omnia to /opt/omnia/shard_libraries/ inside omnia_core container
    echo -e "${BLUE} Copying shared libraries from container to shared_libraries folder.${NC}"
    podman exec -u root omnia_core cp -r /omnia/shared_libraries/ /opt/omnia/

    # Create the .data directory if it does not exist.
    # This is where the oim_metadata.yml file is stored.
    echo -e "${GREEN} Creating the .data directory if it does not exist.${NC}"
    mkdir -p "$omnia_path/omnia/.data"

    oim_metadata_file="$omnia_path/omnia/.data/oim_metadata.yml"

    if [ ! -f "$oim_metadata_file" ]; then
        echo -e "${GREEN} Creating oim_metadata file${NC}"
        {
            echo "oim_crt: \"podman\""
            echo "oim_shared_path: $omnia_path"
            echo "omnia_version: $omnia_release"
            echo "oim_hostname: $(hostname)"
            echo "omnia_core_hashed_passwd: $hashed_passwd"
            echo "omnia_share_option: $share_option"
        } >> "$oim_metadata_file"
        if [ "$share_option" = "NFS" ]; then
            {
            echo "nfs_server_ip: $nfs_server_ip"
            echo "nfs_server_share_path: $nfs_server_share_path"
        } >> "$oim_metadata_file"
        fi
    fi

    touch $HOME/.ssh/known_hosts
    # Add entry to /root/.ssh/known_hosts file to prevent errors caused by Known host
    ssh-keygen -R "[localhost]:2222" >/dev/null 2>&1  # Remove existing entry if it exists
    ssh-keyscan -p 2222 localhost 2>/dev/null | grep -v "^#" >> $HOME/.ssh/known_hosts  # Scan and add the new key
}

start_container_session() {

    echo -e "${GREEN}
    ------------------------------------------------------------------------------------------------------------------------------------------
            Omnia Core container running successfully.

            Entering the container from Omnia Infrastructure Manager(OIM):
            Through podman:
            # podman exec -it -u root omnia_core bash

            Direct SSH:
            # ssh omnia_core

            You are now in the Omnia environment.

            The following are the main directories available in the Omnia core container:

            - The shared directory, which is mapped to $omnia_path in OIM: /opt/omnia
            - The input directory: /opt/omnia/input
            - The Omnia source code directory: /omnia
            - The Omnia playbooks logs directory: /opt/omnia/log/core/playbooks

            It's important to note:
                - Files placed in the shared directory should not be manually deleted.
                - Use the playbook /omnia/utils/oim_cleanup.yml to safely remove the shared directory and Omnia containers (except the core container).
                - If you need to delete the core container or redeploy the core container with new input configs, please rerun the omnia_startup.sh script.
                - Provide any file paths (ISO, mapping files, etc.) that are mentioned in input files in the /opt/omnia directory.

    --------------------------------------------------------------------------------------------------------------------------------------------------
    ${NC}"

    # Waiting for container to be ready
    sleep 2

    # Entering Omnia-core container
    ssh omnia_core
}


# Main function to check if omnia_core container is already running.
# If yes, ask the user if they want to cleanup or reinstall.
# If no, set it up.
main() {
    # Check if any other containers with 'omnia' in their name are running
    other_containers=$(podman ps -a --format '{{.Names}}' | grep -E 'omnia' | grep -v 'omnia_core')

    # If there are any, exit
    if [ -n "$other_containers" ]; then
        echo -e "${RED} There are other omnia container running.${NC}"
        echo -e "${GREEN} Execute oim_cleanup.yml first to cleanup all containers.${NC}"
        exit 1
    fi

    # Check if the omnia_core container is already running
    running_containers=$(podman ps -a --format '{{.Names}} {{.State}}' | grep -E 'omnia_core')

    # If yes, set the variable to true
    if [ -n "$running_containers" ]; then
        core_container_status=true
    fi

    # If core container is running
    if [ "$core_container_status" = true ]; then
        if [ -n "$(echo "$running_containers" | grep -E 'running')" ]; then
            echo -e "${GREEN} Omnia core container is already running.${NC}"
            echo -e "${GREEN} Do you want to:${NC}"
            echo -e "${GREEN} 1. Reinstall the container.${NC}"
            echo -e "${GREEN} 2. Delete the container and configurations.${NC}"
            echo -e "${GREEN} 3. Exit. ${NC}"

            # Get user input
            read -p " Enter your choice (1 or 2): " choice

            # If the user wants to reinstall, call the remove_container function, and then call the setup_omnia_core function
            if [ "$choice" = "1" ]; then
                echo -e "${GREEN} What configuration do you want to use for reinstallation:${NC}"
                echo -e "${GREEN} 1. Retain Existing configuration.${NC}"
                echo -e "${GREEN} 2. Overwrite and create new configuration.${NC}"
                echo -e "${GREEN} 3. Exit. ${NC}"
                read -p " Enter your choice (1 or 2): " choice

                # If the user wants to retain existing configuration, call the remove_container function
                if [ "$choice" = "1" ]; then
                    fetch_config
                    remove_container
                    setup_container
                    start_container_session
                # If the user wants to overwrite and create new configuration, call the cleanup_omnia_core function
                elif [ "$choice" = "2" ]; then
                    cleanup_omnia_core
                    setup_omnia_core
                # If the user wants to exit, exit
                elif [ "$choice" = "3" ]; then
                    exit
                fi
            # If the user wants to cleanup, call the cleanup function
            elif [ "$choice" = "2" ]; then
                cleanup_omnia_core
            # If the user wants to exit, exit
            elif [ "$choice" = "3" ]; then
                exit
            fi
        else
            # If omnia_core container exists and is not running call the remove_container function

            echo -e "${RED} The Omnia Core container is present but not in running state.${NC}"
            echo -e "${GREEN} Only the core container can be cleanup can be performed.${NC}"
            echo -e "${GREEN} Container Configurations in the shared directory will not be cleaned up.${NC}"
            echo -e "${GREEN} Do you want to preform cleanup:${NC}"
            echo -e "${GREEN} 1. Yes.${NC}"
            echo -e "${GREEN} 2. No. ${NC}"
            read -p " Enter your choice (1 or 2): " choice
            if [ "$choice" = "1" ]; then
                remove_container
            elif [ "$choice" = "2" ]; then
                exit
            fi
        fi

    # If core container is not present
    else

        # Start the container setup
        echo -e "${GREEN}Starting Omnia core container setup.${NC}"
        setup_omnia_core
    fi
}

# Call the main function
main
