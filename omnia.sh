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
omnia_release=2.1.0.0

core_container_status=false
omnia_path=""
hashed_passwd=""
domain_name=""

is_local_ip() {
    local ip_to_check="$1"

    # Get all local IP addresses (excluding loopback)
    local local_ips
    local_ips=$(hostname -I)

    # Check if the IP matches any local IP
    if echo "$local_ips" | grep -qw "$ip_to_check"; then
        return 0  # IP is local
    else
        return 1  # IP is not local
    fi
}

# Container-side paths (used inside podman exec commands)
CONTAINER_INPUT_DIR="/opt/omnia/input"
CONTAINER_BACKUPS_DIR="/opt/omnia/backups"
CONTAINER_METADATA_FILE="/opt/omnia/.data/oim_metadata.yml"

# Host-side paths (initialized dynamically after omnia_path is set)
OMNIA_INPUT_DIR=""
OMNIA_METADATA_DIR=""
OMNIA_METADATA_FILE=""

update_metadata_upgrade_backup_dir() {
    local backup_dir="$1"

    if ! podman ps --format '{{.Names}}' | grep -qw "omnia_core"; then
        echo "[ERROR] [ORCHESTRATOR] omnia_core container is not running"
        return 1
    fi

    podman exec -u root omnia_core bash -c "
        set -e
        if [ ! -f '$CONTAINER_METADATA_FILE' ]; then
            echo '[ERROR] Metadata file not found inside container: $CONTAINER_METADATA_FILE' >&2
            exit 1
        fi
        if grep -q '^upgrade_backup_dir:' '$CONTAINER_METADATA_FILE'; then
            sed -i 's|^upgrade_backup_dir:.*|upgrade_backup_dir: ${backup_dir}|' '$CONTAINER_METADATA_FILE'
        else
            echo 'upgrade_backup_dir: ${backup_dir}' >> '$CONTAINER_METADATA_FILE'
        fi
    "
}



check_internal_nfs_export() {
    nfs_server_ip=$1
    nfs_server_share_path=$2

    if is_local_ip "$nfs_server_ip"; then
        echo "The provided NFS server IP ($nfs_server_ip) belongs to the current system."
    else
        echo "The provided NFS server IP ($nfs_server_ip) is NOT the current system's IP."
        exit 1
    fi

    # Query the remote server for exports
    exports=$(showmount -e "$nfs_server_ip" 2>/dev/null)

    if [[ $? -ne 0 ]]; then
        echo -e "${RED}ERROR: Unable to contact NFS server at $nfs_server_ip. Ensure NFS and rpcbind are running, and firewall allows access.${NC}"
        exit 1
    fi

    # Check if path is in the export list
    if echo "$exports" | awk '{print $1}' | grep -Fxq "$nfs_server_share_path"; then
        echo -e "${GREEN}Path $nfs_server_share_path is exported by $nfs_server_ip.${NC}"
    else
        echo -e "${RED}ERROR: Path $nfs_server_share_path is NOT exported by $nfs_server_ip.${NC}"
        exit 1
    fi
}

display_supported_use_cases() {
    # Color definitions
    BLUE='\033[1;34m'
    YELLOW='\033[1;33m'
    GREEN='\033[1;32m'
    NC='\033[0m' # No Color

    # Introductory Guidance
    echo -e "${BLUE} ----------------- Omnia Shared Path Configuration ---------------- ${NC}"
    echo -e "${BLUE} Please choose the type of Omnia shared path in Omnia Infrastructure Manager (OIM): ${NC}"
    echo -e "${BLUE} It is recommended to use a external NFS share for the Omnia shared path. ${NC}"
    echo -e "${BLUE} If you are not using NFS, make sure enough space is available on the disk. ${NC}"
    echo -e "${YELLOW} Using a Extrenal NFS share is mandatory for Omnia shared path if you are planning to have high availability in OIM or require K8s service cluster. ${NC}"
    echo -e "\nSupported Use Cases:\n"

    # Table content
    {
        echo -e "Share Option\tType\tDescription\tAdditional Info"
        echo -e "${GREEN}NFS\tExternal\tExternal NFS server(outside OIM) created by user\tMust be reachable from OIM and service nodes. Mounts on OIM. Recommended for HA and hierarchical clusters.${NC}"
        echo -e "NFS\tInternal\tNFS server created by user in OIM\tUsed only for flat provisioning. No HA or k8s service cluster support. No mount performed."
        echo -e "Local\tDisk\tDisk storage in OIM\tUsed only for flat provisioning. No HA or hierarchical support."
    } | column -t -s $'\t'
}


# This function is responsible for initializing the Omnia core container
# It prompts the user for the Omnia shared path and the root password.
# It checks if the Omnia shared path exists.
setup_omnia_core() {
    # Validate the system environment
    validate_oim

    # Initialize the container configuration
    init_container_config

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
    # Block if critical service containers exist
    critical_running=$(podman ps --format '{{.Names}}' | grep -E 'pulp|registry|minio-server|postgres|step-ca|hydra|smd|opaal-idp|bss|opaal|cloud-init-server|haproxy|coresmd')
    if [ -n "$critical_running" ]; then
        echo -e "${RED}Failed to intiatiate omnia_core container cleanup. There are other critical service containers still running:${NC}"
        echo "$critical_running"
        echo -e "${GREEN}Run oim_cleanup.yml first to cleanup all containers.${NC}"
        exit 1
    fi

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
    rm -rf $omnia_path/omnia/{hosts,input,log,pulp,provision,pcs,ssh_config,tmp,.data}

    # Unmount the NFS shared path if the share option is NFS.
    if [ "$share_option" = "NFS" ] && [ "$nfs_type" = "external" ]; then
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
    # Block if critical service containers exist
    critical_running=$(podman ps --format '{{.Names}}' | grep -E 'pulp|registry|minio-server|postgres|step-ca|hydra|smd|opaal-idp|bss|opaal|cloud-init-server|haproxy|coresmd')
    if [ -n "$critical_running" ]; then
        echo -e "${RED}Failed to intiatiate omnia_core container cleanup. There are other critical service containers still running:${NC}"
        echo "$critical_running"
        echo -e "${GREEN}Run oim_cleanup.yml first to cleanup all containers.${NC}"
        exit 1
    fi

    # Remove the container.
    echo -e "${BLUE} Removing the Omnia core container.${NC}"
    if systemctl stop omnia_core.service; then
        echo -e "${GREEN} Omnia core container has been removed.${NC}"
        # Remove the systemd generator symlinks.
        echo -e "${GREEN} Cleaning up systemd generator symlinks.${NC}"
        rm -f /run/systemd/generator/omnia_core.service
        rm -f /run/systemd/generator/multi-user.target.wants/omnia_core.service
        rm -f /run/systemd/generator/default.target.wants/omnia_core.service

        echo -e "${GREEN} Cleaning up omnia_core.container.${NC}"
        rm -f /etc/containers/systemd/omnia_core.container

    # Remove the omnia_core.service file.
        rm -f /etc/systemd/system/omnia_core.service
        systemctl daemon-reload
        systemctl reset-failed omnia_core.service
    # check if service is removed
        if systemctl status omnia_core.service >/dev/null 2>&1; then
            echo -e "${RED} Failed to remove Omnia core service.${NC}"
        else
            echo -e "${GREEN} Omnia core service has been removed.${NC}"
        fi    
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
    # Display the supported use cases
    display_supported_use_cases

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

            # Check if the Omnia shared path is absolute path and path exists.
            if [[ "$omnia_path" != /* ]] || [ ! -d "$omnia_path" ]; then
                echo -e "${RED} Omnia shared path is not an absolute path or does not exist! Please re-run omnia.sh --install with valid Omnia shared path.${NC}"
                exit 1
            fi
            ;;
        "NFS")
            echo -e "${BLUE} Select NFS type:${NC}"
            select nfs_type in "External (Recommended)" "Internal"; do
                case $nfs_type in
                    "External (Recommended)")
                        echo -e "${BLUE} Please provide the external NFS server IP:${NC}"
                        read -p "External NFS server IP: " nfs_server_ip

                        echo -e "${BLUE} Please provide the external NFS server share path:${NC}"
                        read -p "External NFS share path: " nfs_server_share_path

                        echo -e "${BLUE} Please provide the OIM client share path (mount target):${NC}"
                        read -p "Omnia shared path: " omnia_path

                        # Validate Omnia shared path is absolute
                        if [[ "$omnia_path" != /* ]]; then
                            echo -e "${RED}Omnia shared path must be an absolute path.${NC}"
                            exit 1
                        fi

                        nfs_type="external"
                        break
                        ;;
                    "Internal")
                        echo -e "${BLUE} Please provide the OIM server IP:${NC}"
                        read -p "OIM server IP: " nfs_server_ip

                        echo -e "${BLUE} Please provide the OIM server share path:${NC}"
                        read -p "OIM server share path: " nfs_server_share_path

                        echo -e "${BLUE} Checking if the OIM server share path is mounted${NC}"
                        check_internal_nfs_export "$nfs_server_ip" "$nfs_server_share_path"

                        # Note: No mounting performed here
                        echo -e "${YELLOW}Note: Internal NFS does not support HA OIM or hierarchical cluster. Proceeding...${NC}"
                        nfs_type="internal"
                        omnia_path="$nfs_server_share_path"
                        break
                        ;;
                    *)
                        echo -e "${RED}Invalid option. Please choose 1 or 2.${NC}"
                        ;;
                esac
            done
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

        # Mount NFS server share path in Omnia share path
        if [[ "$nfs_type" == "external" ]]; then

            if is_local_ip "$nfs_server_ip"; then
                echo -e "${RED} Error: NFS server $nfs_server_ip is a local IP.${NC}"
                echo -e "${RED} Please provide an external NFS server IP or re-run omnia.sh --install with valid options.${NC}"
                exit 1
            fi

            # Validate if NFS server is reachable
            echo -e "${BLUE} Validating if NFS server is reachable.${NC}"
            ping -c1 -W1 $nfs_server_ip > /dev/null
            if [ $? -ne 0 ]; then
                echo -e "${RED} NFS server $nfs_server_ip is not reachable.${NC}"
                exit 1
            fi

            echo -e "${BLUE} Mounting NFS server share path in Omnia share path.${NC}"
            mount -t nfs -o nosuid,rw,sync,hard,intr,timeo=30 "$nfs_server_ip:$nfs_server_share_path" "$omnia_path"
            if [[ $? -ne 0 ]]; then
                echo -e "${RED} Failed to mount NFS. Please check the IP and path.${NC}"
                exit 1
            fi
            # Validate if NFS server share path is mounted
            echo -e "${BLUE} Validating if NFS server share path is mounted.${NC}"
            # strip the trailing slash from nfs_server_share_path
            nfs_server_share_path="${nfs_server_share_path%/}"
            if grep -qs "$nfs_server_ip:$nfs_server_share_path" /proc/mounts; then
                echo -e "${GREEN} NFS server share path is mounted.${NC}"
            else
                echo -e "${RED} NFS server share path is not mounted. Provide valid NFS server details. ${NC}"
                exit 1
            fi
            # Add NFS server share to /etc/fstab to mount on startup
            echo "$nfs_server_ip:$nfs_server_share_path $omnia_path nfs nosuid,rw,sync,hard,intr" >> /etc/fstab
        else
            echo -e "${BLUE} Using internal NFS path without mounting.${NC}"
        fi

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

    # Copy the omnia_core ssh config to the shared path.
    echo -e "${GREEN} Copying the omnia_core ssh config to the omnia shared path.${NC}"
    cp "$HOME/.ssh/config" "$omnia_path/omnia/ssh_config/.ssh/config"

    # Copy the oim_rsa ssh key to the shared path.
    echo -e "${GREEN} Copying the oim_rsa ssh key to the omnia shared path.${NC}"
    cp "$HOME/.ssh/oim_rsa" "$omnia_path/omnia/ssh_config/.ssh/oim_rsa"

    # Copy the ssh private key to the omnia shared path.
    echo -e "${GREEN} Copying the ssh private key to the omnia shared path.${NC}"
    cp $ssh_key_file "$omnia_path/omnia/ssh_config/.ssh/id_rsa"

    # Copy the ssh public key to the omnia shared path.
    echo -e "${GREEN} Copying the ssh public key to the omnia shared path.${NC}"
    cp $ssh_key_file.pub "$omnia_path/omnia/ssh_config/.ssh/id_rsa.pub"

    # Get the ssh public key.
    ssh_public_key="$(cat /root/.ssh/oim_rsa.pub)"

    validate_nfs_server

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

    # Initialize host-side path variables based on user-provided omnia_path
    OMNIA_INPUT_DIR="$omnia_path/omnia/input"
    OMNIA_METADATA_DIR="$omnia_path/omnia/.data"
    OMNIA_METADATA_FILE="$omnia_path/omnia/.data/oim_metadata.yml"
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
            nfs_type)
                # Assign the share option.
                nfs_type=$(echo "$value" | tr -d '[:space:]')
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

    # Initialize host-side path variables based on fetched omnia_path
    OMNIA_INPUT_DIR="$omnia_path/omnia/input"
    OMNIA_METADATA_DIR="$omnia_path/omnia/.data"
    OMNIA_METADATA_FILE="$omnia_path/omnia/.data/oim_metadata.yml"
}

# Validates the OIM (Omnia Infrastructure Manager) by checking if the hostname is
# configured with a domain name, checking if Podman is installed, enabling and
# starting the Podman socket.
validate_oim() {
    # Check if the hostname is set
    hostname_value=$(hostname)
    if [[ -z "$hostname_value" ]]; then
        echo -e "${RED}Hostname is not set!${NC}"
        exit 1
    fi

    # Check if the hostname is static
    static_hostname=$(hostnamectl --static)
    current_hostname=$(hostname)
    if [[ "$static_hostname" != "$current_hostname" ]]; then
        echo -e "${RED}Static Hostname is unset. Current: '$current_hostname', Static: '$static_hostname'${NC}"
        echo -e "${RED}Please set the static hostname and try again.${NC}"
        echo -e "${BLUE}Command to set hostname: hostnamectl set-hostname <hostname>${NC}"
        echo -e "${RED}Exiting...${NC}"
        exit 1
    fi

    # Check if the hostname is configured with a domain name.
    domain_name=$(hostname -d)
    if [[ -n "$domain_name" ]]; then
        echo -e "${BLUE}Hostname is configured with a domain name: $domain_name${NC}"
    else
        echo -e "${RED}Invalid hostname, hostname is not configured with a domain name!${NC}"
        exit 1
    fi

    # Detect OIM timezone from systemd in a stable, case‑independent way
    oim_timezone=$(timedatectl show -p Timezone --value 2>/dev/null)

    # Fallbacks if needed (non‑systemd or old timedatectl)
    if [[ -z "$oim_timezone" ]]; then
        if [[ -f /etc/timezone ]]; then
            # Debian/Ubuntu style
            oim_timezone=$(< /etc/timezone)
        elif [[ -L /etc/localtime ]]; then
            # Derive from /etc/localtime symlink
            oim_timezone=$(readlink -f /etc/localtime | sed -n 's|^.*zoneinfo/||p')
        fi
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

# Checks if the required directories for Omnia are present.
# This function iterates over a list of required directories/files and checks if each one exists.
check_required_directories() {
    required_paths=(
        "$omnia_path/omnia"
        "$omnia_path/omnia/ssh_config/.ssh"
        "$omnia_path/omnia/log/core/container"
        "$omnia_path/omnia/hosts"
        "$omnia_path/omnia/pulp/pulp_ha"
    )

    missing_paths=()

    for path in "${required_paths[@]}"; do
        if [ ! -e "$path" ]; then  # Checks both files and directories
            missing_paths+=("$path")
        fi
    done

    if [ "${#missing_paths[@]}" -ne 0 ]; then
        echo -e "${RED}Error: The following required files or directories are missing:${NC}"
        echo -e "${RED}${missing_paths[*]}${NC}"
        echo -e "User can not Retain Existing configuration"
        echo
        echo -e "${YELLOW}Instructions:${NC}"
        echo -e "${YELLOW}* Backup any existing files if required${NC}"
        echo -e "${YELLOW}* Run ./omnia.sh --install and choose:${NC}"
        echo -e "${YELLOW}    Options:${NC}"
        echo -e "${YELLOW}      -> Reinstall the container${NC}"
        echo -e "${YELLOW}      -> Overwrite and create new configuration${NC}"
        exit 1
    fi
}

# Sets up the Omnia core container.
# This function pulls the Omnia core Podman image and runs the container.
# Creates a Quadlet service for the container and also creates a metadata file.
# It defines the container options and runs the container.
setup_container() {
    container_name="omnia_core"
    echo "==> Setting up $container_name container"

    # SELinux option handling
    selinux_option=":z"
    if [ "$share_option" = "NFS" ] && [ "$nfs_type" = "external" ]; then
        selinux_option=""
    fi

    # Check if RHEL subscription is enabled
    subscription_enabled=false
    if [ -d "/etc/pki/entitlement" ] && [ "$(ls -A /etc/pki/entitlement/*.pem 2>/dev/null)" ]; then
        subscription_enabled=true
    fi

    # --- Generate Quadlet container file ---
    cat > /etc/containers/systemd/${container_name}.container <<EOF
# ===============================================================
# $container_name Quadlet Service
# Generated dynamically by omnia.sh
# ===============================================================
[Unit]
Description=${container_name^} Container

[Container]
ContainerName=${container_name}
HostName=${container_name}
Image=${container_name}:1.1
Network=host

# Capabilities
AddCapability=CAP_AUDIT_WRITE

# Volumes
Volume=${omnia_path}/omnia:/opt/omnia${selinux_option}
Volume=${omnia_path}/omnia/ssh_config/.ssh:/root/.ssh${selinux_option}
Volume=${omnia_path}/omnia/log/core/container:/var/log${selinux_option}
Volume=${omnia_path}/omnia/hosts:/etc/hosts${selinux_option}
Volume=${omnia_path}/omnia/pulp/pulp_ha:/root/.config/pulp${selinux_option}
EOF

    # Add subscription volume mounts only if subscription is enabled
    if [ "$subscription_enabled" = true ]; then
        cat >> /etc/containers/systemd/${container_name}.container <<EOF
Volume=/etc/pki/entitlement:/etc/pki/entitlement:ro,z
Volume=/etc/yum.repos.d/redhat.repo:/etc/yum.repos.d/redhat.repo:ro,z
EOF
    fi

    cat >> /etc/containers/systemd/${container_name}.container <<EOF

[Service]
Restart=always

[Install]
WantedBy=multi-user.target default.target

EOF

    # Create the .data directory if it does not exist.
    # This is where the oim_metadata.yml file is stored.
    echo -e "${GREEN} Creating the .data directory if it does not exist.${NC}"
    mkdir -p "$OMNIA_METADATA_DIR"

    oim_metadata_file="$OMNIA_METADATA_FILE"

    if [ ! -f "$oim_metadata_file" ]; then
        echo -e "${GREEN} Creating oim_metadata file${NC}"
        {
            echo "oim_crt: \"podman\""
            echo "oim_shared_path: $omnia_path"
            echo "omnia_version: $omnia_release"
            echo "oim_hostname: $(hostname)"
            echo "oim_node_name: $(hostname -s)"
            echo "domain_name: $domain_name"
            echo "oim_timezone: $oim_timezone"
            echo "omnia_core_hashed_passwd: $hashed_passwd"
            echo "omnia_share_option: $share_option"
        } >> "$oim_metadata_file"
        if [ "$share_option" = "NFS" ]; then
            {
            echo "nfs_server_ip: $nfs_server_ip"
            echo "nfs_server_share_path: $nfs_server_share_path"
            echo "nfs_type: $nfs_type"
        } >> "$oim_metadata_file"
        fi
    fi

    # --- Remove old service if exists ---
    if systemctl list-unit-files | grep -q "${container_name}.service"; then
        systemctl stop ${container_name}.service
        systemctl disable ${container_name}.service
        rm -f /etc/systemd/system/${container_name}.service
    fi

    # --- Reload systemd so Quadlet generates the service ---
    systemctl daemon-reexec
    systemctl daemon-reload
    systemctl start ${container_name}.service

    # --- Start the container via Quadlet ---
    echo "==> ${container_name} container deployed and starting via Quadlet"

    # --- Wait for container to be running ---
    echo "Waiting for $container_name container to start..."
    for i in {1..30}; do
        if podman ps --format '{{.Names}}' | grep -qw "$container_name"; then
            echo "$container_name container is running."
            break
        else
            sleep 1
        fi
    done

    if ! podman ps --format '{{.Names}}' | grep -qw "$container_name"; then
        echo -e "${RED}Error: $container_name container failed to start.${NC}"
        rm -rf "$OMNIA_METADATA_FILE"
        exit 1
    fi

    systemctl start firewalld
    systemctl enable firewalld
    firewall-cmd --permanent --zone=public --add-port=2222/tcp
    firewall-cmd --reload
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
    mkdir -p "$OMNIA_INPUT_DIR/"

    # Create the default.yml file if it does not exist.
    # This file contains the name of the project.
    if [ ! -f "$OMNIA_INPUT_DIR/default.yml" ]; then
        echo -e "${BLUE} Creating default.yml file.${NC}"
        {
            echo "# This file defines the project name."
            echo "# The name of the project should be set in a directory under input."
            echo "project_name: project_default"
        } >> "$OMNIA_INPUT_DIR/default.yml"
    fi

    # Copy input files from /omnia to /opt/omnia/project_default/ inside omnia_core container
    podman exec -u root omnia_core bash -c "cd /omnia && git pull"
    echo -e "${BLUE} Moving input files from /omnia dir to project_default folder.${NC}"
    podman exec -u root omnia_core bash -c "
    mkdir -p /opt/omnia/input/project_default
    cp -r /omnia/input/* /opt/omnia/input/project_default
    rm -rf /omnia/input
    rm -rf /omnia/omnia.sh"

    init_ssh_config
}

validate_nfs_server() {

    # Validate NFS server permission
    if [ "$share_option" = "NFS" ]; then
        # Create a temporary file inside $omnia_path
        temp_file="$omnia_path/temp_file"
        touch "$temp_file"
        # Check if the file can be chown to root
        if chown root:root "$temp_file"; then
            rm "$temp_file"
        else
            echo "Error: Unable to chown file to root in $omnia_path. NFS server permission validation failed. Please ensure no_root_squash option is enabled in the NFS export configuration."
            exit 1
        fi
        if [ "`ls -ld $omnia_path/omnia/ssh_config/.ssh/id_rsa | awk '{print $3 ":" $4}'`" != "root:root" ]; then
            echo "Error: The $omnia_path/omnia/ssh_config/.ssh/id_rsa file should be owned by root:root. NFS server permission validation failed. Please verify the NFS export configuration."
            exit 1
        fi
    fi

}

init_ssh_config() {
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
                - If you need to delete the core container, please run the omnia.sh script with --uninstall option.
                - If you need to  redeploy the core container with new input configs, please rerun the omnia.sh script with --install option.
                - Provide any file paths (ISO, mapping files, etc.) that are mentioned in input files in the /opt/omnia directory.
                - The domain name that will be used for Omnia is $domain_name, if you wish to change the domain name please cleanup Omnia,
                  change the Omnia Infrastructure Manager's domain name and rerun omnia.sh script with --install option.

    --------------------------------------------------------------------------------------------------------------------------------------------------
    ${NC}"

    # Entering Omnia-core container
    ssh omnia_core
}

show_help() {
    echo "Usage: $0 [--install | --uninstall | --upgrade | --version | --help]"
    echo "  -i, --install     Install and start the Omnia core container"
    echo "  -u, --uninstall   Uninstall the Omnia core container and clean up configuration"
    echo "      --upgrade     Upgrade the Omnia core container from image tag 1.0 to 1.1"
    echo "  -v, --version     Display Omnia version information"
    echo "  -h, --help        More information about usage"
}

install_omnia_core() {
    local omnia_core_tag="1.1"
    local omnia_core_registry=""
    
    # Check if local omnia_core:1.1 exists
    if podman inspect omnia_core:${omnia_core_tag} >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Omnia core image (omnia_core:${omnia_core_tag}) found locally.${NC}"
    # Check if latest exists for backward compatibility
    elif podman inspect omnia_core:latest >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Omnia core image (omnia_core:latest) found locally.${NC}"
        # Tag it as 1.1 for consistency
        podman tag omnia_core:latest omnia_core:${omnia_core_tag}
    else
        echo -e "${RED}ERROR: Omnia core image (omnia_core:${omnia_core_tag}) not found locally.${NC}"
        echo -e "${YELLOW}Omnia no longer pulls images from Docker Hub. Build/load the image locally and retry.${NC}"
        echo ""
        echo -e "${YELLOW}One way to build the image locally:${NC}"
        echo -e "1. Clone the Omnia Artifactory repository:"
        echo -e "   git clone https://github.com/dell/omnia-artifactory -b omnia-container"
        echo -e "2. Navigate to the repository directory:"
        echo -e "   cd omnia-artifactory"
        echo -e "3. Build the core image locally (loads into local Podman by default):"
        echo -e "   ./build_images.sh core omnia_branch=<version/branch_name>"
        echo ""
        echo -e "${YELLOW}Then re-run:${NC}"
        echo -e "   ./omnia.sh --install"
        exit 1
    fi

    # Check if any other containers with 'omnia' in their name are running
    other_containers=$(podman ps -a --format '{{.Names}}' | grep -E 'omnia' | grep -v 'omnia_core')

    # If there are any, exit
    if [ -n "$other_containers" ]; then
        echo -e "${RED} Failed to intiatiate omnia_core container cleanup. There are other omnia container running.${NC}"
        echo -e "${GREEN} Execute oim_cleanup.yml first to cleanup all containers.${NC}"
        ssh omnia_core
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
            PS3="Select the option number: "

            select opt in "Enter omnia_core container" "Reinstall the container" "Exit"; do
                case $opt in
                    "Enter omnia_core container")
                        choice=1
                        break
                        ;;
                    "Reinstall the container")
                        choice=2
                        break
                        ;;
                    "Exit")
                        echo "Exiting the script."
                        exit 0
                        ;;
                    *)
                        echo "Invalid choice. Please try again."
                        continue
                        ;;
                esac
            done

            # If the user wants to enter omnia_core container
            if [ "$choice" = "1" ]; then
                start_container_session
            fi
            # If the user wants to reinstall, call the remove_container function, and then call the setup_omnia_core function
            if [ "$choice" = "2" ]; then
                # Block if critical service containers exist
                critical_running=$(podman ps --format '{{.Names}}' | grep -E 'pulp|registry|minio-server|postgres|step-ca|hydra|smd|opaal-idp|bss|opaal|cloud-init-server|haproxy|coresmd')
                if [ -n "$critical_running" ]; then
                    echo -e "${RED}Failed to intiatiate omnia_core container cleanup. There are other critical service containers still running:${NC}"
                    echo "$critical_running"
                    echo -e "${GREEN}Run oim_cleanup.yml first to cleanup all containers.${NC}"
                    exit 1
                fi
                echo -e "${GREEN} What configuration do you want to use for reinstallation:${NC}"

                PS3="Select the option number: "

                select opt in "Retain Existing configuration" "Overwrite and create new configuration" "Exit"; do
                    case $opt in
                        "Retain Existing configuration")
                            choice=1
                            break
                            ;;
                        "Overwrite and create new configuration")
                            choice=2
                            break
                            ;;
                        "Exit")
                            echo "Exiting the script."
                            exit 0
                            ;;
                        *)
                            echo "Invalid choice. Please try again."
                            continue
                            ;;
                    esac
                done

                # If the user wants to retain existing configuration, call the remove_container function
                if [ "$choice" = "1" ]; then
                    fetch_config
                    check_required_directories
                    remove_container
                    setup_container
                    init_ssh_config
                    start_container_session
                # If the user wants to overwrite and create new configuration, call the cleanup_omnia_core function
                elif [ "$choice" = "2" ]; then
                    cleanup_omnia_core
                    setup_omnia_core
                fi
            fi
        else
            # If omnia_core container exists and is not running call the remove_container function

            echo -e "${RED} The Omnia Core container is present but not in running state.${NC}"
            echo -e "${GREEN} Only the core container can be cleanup can be performed.${NC}"
            echo -e "${GREEN} Container Configurations in the shared directory will not be cleaned up.${NC}"
            echo -e "${GREEN} Do you want to perform cleanup:${NC}"
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

# Check if Omnia core container is running
check_container_status() {
    # Check if the Omnia core container is running
    if ! podman ps --format '{{.Names}}' | grep -qw "omnia_core"; then
        echo -e "${RED}ERROR: Omnia core container is not running.${NC}"
        exit 1
    fi
}

# Function to display version information
display_version() {
    # Check if metadata file exists and Omnia core container is running
    check_container_status
    
    # Fetch the metadata from the oim_metadata.yml file in the container
    echo -e "${GREEN} Fetching metadata from omnia_core container...${NC}"
    core_config=$(podman exec omnia_core /bin/bash -c 'cat /opt/omnia/.data/oim_metadata.yml')
    
    # Extract Omnia version from metadata file
    omnia_version=$(echo "$core_config" | grep "omnia_version:" | cut -d':' -f2 | tr -d ' \t\n\r')
    
    # Display version information
    echo "Omnia version: $omnia_version"
    
    # Return exit code 0 on success
    exit 0
}

phase1_validate() {
    local current_image
    local core_config
    local previous_omnia_version
    local shared_path

    echo "[INFO] [ORCHESTRATOR] Phase 1: Pre-Upgrade Validation"

    if [ "$(id -u)" -ne 0 ]; then
        if ! sudo -n true >/dev/null 2>&1; then
            echo "[ERROR] [ORCHESTRATOR] Prerequisite failed: run as root or configure passwordless sudo"
            return 1
        fi
    fi

    if ! podman ps --format '{{.Names}}' | grep -qw "omnia_core"; then
        echo "[ERROR] [ORCHESTRATOR] Prerequisite failed: omnia_core container is not running"
        return 1
    fi

    core_config=$(podman exec omnia_core /bin/bash -c 'cat /opt/omnia/.data/oim_metadata.yml' 2>/dev/null)
    if [ -z "$core_config" ]; then
        echo "[ERROR] [ORCHESTRATOR] Unable to read oim_metadata.yml from omnia_core container"
        return 1
    fi

    previous_omnia_version=$(echo "$core_config" | grep "^omnia_version:" | cut -d':' -f2 | tr -d ' \t\n\r')
    if [ -z "$previous_omnia_version" ]; then
        echo "[ERROR] [ORCHESTRATOR] omnia_version not found in oim_metadata.yml"
        return 1
    fi

    if [ "$previous_omnia_version" != "2.0.0.0" ]; then
        echo "[ERROR] [ORCHESTRATOR] Previous Omnia version mismatch: expected 2.0.0.0, got: $previous_omnia_version"
        return 1
    fi

    shared_path=$(echo "$core_config" | grep "^oim_shared_path:" | cut -d':' -f2- | tr -d ' \t\n\r')
    if [ -z "$shared_path" ]; then
        echo "[ERROR] [ORCHESTRATOR] oim_shared_path not found in oim_metadata.yml"
        return 1
    fi

    omnia_path="$shared_path"

    if [ ! -d "$omnia_path" ]; then
        echo "[ERROR] [ORCHESTRATOR] Shared path from metadata does not exist on host: $omnia_path"
        return 1
    fi

    if [ ! -w "$omnia_path" ]; then
        echo "[ERROR] [ORCHESTRATOR] Permission denied: no write permission on shared path: $omnia_path"
        return 1
    fi

    current_image=$(podman inspect omnia_core --format '{{.ImageName}}' 2>/dev/null)
    if [ -z "$current_image" ]; then
        echo "[ERROR] [ORCHESTRATOR] Unable to inspect omnia_core container image"
        return 1
    fi

    if ! echo "$current_image" | grep -qE '(:|@)1\.0(\b|$)'; then
        echo "[ERROR] [ORCHESTRATOR] Container version mismatch: expected 1.0, got: $current_image"
        return 1
    fi

    echo "[INFO] [ORCHESTRATOR] Container version validated: 1.0 (Omnia 2.0.0.0)"

   

    if ! podman inspect "omnia_core:1.1" >/dev/null 2>&1; then
        echo "[ERROR] [ORCHESTRATOR] Target image missing locally: omnia_core:1.1"
        echo "[ERROR] [ORCHESTRATOR] Omnia does not pull from Docker Hub. Build/load the image locally and retry."
        return 1
    fi

    echo "[INFO] [ORCHESTRATOR] Phase 1: Validation passed"
    return 0
}

phase2_approval() {
    local backup_base default_backup_dir

    echo "[INFO] [ORCHESTRATOR] Phase 2: Approval Gate"
    echo "============================================"
    echo "OMNIA UPGRADE SUMMARY"
    echo "============================================"
    echo "Current Container Tag: 1.0"
    echo "Target Container Tag:  1.1"
    echo "Current Omnia Release: 2.0.0.0"
    echo "Target Omnia Release:  2.1.0.0"
    echo "New Features:"
    echo "  - Add and remove node for slurm cluster"
    echo "  - Additional Package Installation"
    echo "============================================"

    default_backup_dir="$CONTAINER_BACKUPS_DIR/upgrade"
    backup_base="$default_backup_dir"

    echo "[INFO] [ORCHESTRATOR] Backup destination: $backup_base"

    if ! update_metadata_upgrade_backup_dir "$backup_base"; then
        echo "[ERROR] [ORCHESTRATOR] Failed to update upgrade backup directory in metadata"
        return 1
    fi

    read -p "Proceed with upgrade? (y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "[INFO] [ORCHESTRATOR] Upgrade cancelled by user"
        return 1
    fi

    OMNIA_UPGRADE_BACKUP_PATH="$backup_base"
    export OMNIA_UPGRADE_BACKUP_PATH

    echo "[INFO] [ORCHESTRATOR] Phase 2: Approval granted"
    return 0
}

phase3_backup_creation() {
    local backup_base="$1"

    echo "[INFO] [ORCHESTRATOR] Phase 3: Backup Creation"

    if ! podman ps --format '{{.Names}}' | grep -qw "omnia_core"; then
        echo "[ERROR] [ORCHESTRATOR] Cannot create backup because omnia_core is not running"
        return 1
    fi

    if [ -z "$backup_base" ]; then
        echo "[ERROR] [ORCHESTRATOR] Backup destination is empty"
        return 1
    fi

    if ! podman exec -u root omnia_core bash -c "
        set -e
        rm -rf '${backup_base%/}/input' '${backup_base%/}/metadata' '${backup_base%/}/configs'
        mkdir -p '${backup_base%/}/input' '${backup_base%/}/metadata' '${backup_base%/}/configs'

        if [ -f '$CONTAINER_INPUT_DIR/default.yml' ]; then
            cp -a '$CONTAINER_INPUT_DIR/default.yml' '${backup_base%/}/input/'
        fi

        if [ -d '$CONTAINER_INPUT_DIR/project_default' ]; then
            cp -a '$CONTAINER_INPUT_DIR/project_default' '${backup_base%/}/input/'
        fi

        if [ ! -f '$CONTAINER_METADATA_FILE' ]; then
            echo '[ERROR] Metadata file not found inside container: $CONTAINER_METADATA_FILE' >&2
            exit 1
        fi
        cp -a '$CONTAINER_METADATA_FILE' '${backup_base%/}/metadata/oim_metadata.yml'
    "; then
        echo "[ERROR] [ORCHESTRATOR] Backup failed; cleaning up partial backup"
        podman exec -u root omnia_core bash -c "rm -rf '${backup_base%/}/input' '${backup_base%/}/metadata' '${backup_base%/}/configs'" >/dev/null 2>&1 || true
        return 1
    fi

    if [ -f "/etc/containers/systemd/omnia_core.container" ]; then
        if ! podman cp "/etc/containers/systemd/omnia_core.container" "omnia_core:${backup_base%/}/configs/omnia_core.container" >/dev/null 2>&1; then
            echo "[ERROR] [ORCHESTRATOR] Failed to backup quadlet container file"
            podman exec -u root omnia_core bash -c "rm -rf '${backup_base%/}/input' '${backup_base%/}/metadata' '${backup_base%/}/configs'" >/dev/null 2>&1 || true
            return 1
        fi
    fi

    echo "[INFO] [ORCHESTRATOR] Backup created at: $backup_base"
    echo "[INFO] [ORCHESTRATOR] Phase 3: Backup completed"
    return 0
}

upgrade_omnia_core() {
    local lock_file="/var/lock/omnia_core_upgrade.lock"
    local backup_base

    if [ -e "$lock_file" ]; then
        echo -e "${RED}ERROR: Upgrade lock exists at $lock_file. Another upgrade may be running.${NC}"
        exit 1
    fi

    mkdir -p "$(dirname "$lock_file")" 2>/dev/null || true
    echo "$$" > "$lock_file" || {
        echo -e "${RED}ERROR: Failed to create lock file: $lock_file${NC}"
        exit 1
    }
    trap 'rm -f "$lock_file"' EXIT

    if ! phase1_validate; then
        echo "[ERROR] [ORCHESTRATOR] Upgrade failed in Phase 1"
        exit 1
    fi

    if ! phase2_approval; then
        exit 0
    fi

    backup_base="$OMNIA_UPGRADE_BACKUP_PATH"
    if [ -z "$backup_base" ]; then
        echo "[ERROR] [ORCHESTRATOR] Backup path is empty"
        exit 1
    fi

    if ! phase3_backup_creation "$backup_base"; then
        echo "[ERROR] [ORCHESTRATOR] Upgrade failed in Phase 3"
        exit 1
    fi

    echo "[INFO] [ORCHESTRATOR] Upgrade tasks for container swap are deferred to a follow-up PR"
    exit 0
}

# Main function to check if omnia_core container is already running.
# If yes, ask the user if they want to enter the container or reinstall.
# If no, set it up.
main() {
    case "$1" in
        --install|-i)
            install_omnia_core
            ;;
        --uninstall|-u)
            cleanup_omnia_core
            ;;
        --upgrade)
            upgrade_omnia_core
            ;;
        --version|-v)
            display_version
            ;;
        --help|-h|"")
            show_help
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
}

# Call the main function
main "$1"
