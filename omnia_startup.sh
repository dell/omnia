#!/bin/bash


# This script is used to generate the Omnia core docker image.
# The image is based on Fedora and uses systemd to start all of the necessary
# services.
#
# This script prompts the user for the persistent volume path and the root
# password. It then checks if the persistent volume path exists.
#
# The script checks if the ssh key file exists. If it does not exist, a new ssh

# Color Definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print prompt for the persistent volume path
echo -e "${BLUE}Please provide Omnia shared path:${NC}"

# Prompt the user for the persistent volume path.
read -p "Enter: " omnia_path

# Check if the persistent volume path exists.
if [ ! -d "$omnia_path" ]; then
    echo -e "${RED}Omnia shared path does not exist!${NC}"
    exit
fi

# The Omnia version. This variable is used to specify the version of the codebase.
OMNIA_VERSION="pub/new_architecture"

# Print prompt for the root password
echo -e "${BLUE}Please provide root password:${NC}"

# Prompt the user for the root password.
read -p "Enter: " -s passwd

# Print prompt for the root password confirmation
echo -e "\n${BLUE}Please confirm password:${NC}"

# Prompt the user for the root password confirmation.
read -s -p "Enter: " cnf_passwd

# Check if the provided passwords match.
if [ "$passwd" != "$cnf_passwd" ]; then
    echo -e "${RED}Invalid root password, passwords do not match!${NC}"
    exit 1
fi

hashed_passwd=$(openssl passwd -1 $passwd)
ssh_key_file="/root/.ssh/id_rsa"

if [ -f "$ssh_key_file" ]; then
    echo -e "${BLUE}Skipping generating new ssh key pair.${NC}"
else
    echo -e "${GREEN}Generating a new ssh key pair.${NC}"
    ssh-keygen -t rsa -b 4096 -C "omnia_oim" -q -N '' -f /root/.ssh/oim_rsa
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
ssh_public_key="$(cat /root/.ssh/id_rsa.pub)"


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
if hostname | grep -q '\.'; then
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

#------------------------------------------------------------------------------------------------
# # Print message for pulling the Omnia core docker image.
# echo -e "${BLUE}Pulling the Omnia core image.${NC}"

# # Pull the Omnia core docker image.
# podman pull omnia_core:latest

# # Print success message
# echo -e "${GREEN}Omnia core image has been pulled.${NC}"
#------------------------------------------------------------------------------------------------

# Print message for building the Omnia core docker image.
echo -e "${GREEN}Building the Omnia core image.${NC}"
podman build --build-arg OMNIA_VERSION="$OMNIA_VERSION" -t omnia_core:latest -f omnia_core


# Print message for running the Omnia core docker image.
echo -e "${GREEN}Running the Omnia core image.${NC}"
podman run -dt --hostname omnia_core --restart=always -v $omnia_path/omnia:/opt/omnia:z -v $omnia_path/omnia/ssh_config/.ssh:/root/.ssh:z -e ROOT_PASSWORD_HASH=$passwd --net=host --name omnia_core --cap-add=CAP_AUDIT_WRITE --replace omnia_core:latest

oim_metadata_file="$omnia_path/omnia/.data/oim_metadata.yml"

if [ ! -f "$oim_metadata_file" ]; then
    echo -e "${GREEN}Creating oim_metadata file${NC}"
    {
        echo "---"
        echo "oim_crt: \"podman\""
        echo "oim_shared_path: $omnia_path"
        echo "omnia_version: 2.0.0.0"
        echo "oim_hostname: $(hostname)"
    } >> "$oim_metadata_file"
fi

echo -e "${GREEN}
----------------------------------------------------------------------
         Omnia Core image built and running successfully.

         Entering the container:
           Though podman:
           # podman exec -it -u root omnia_core bash
           
           Direct SSH:
           # ssh localhost -p 2222

         You are now in the Omnia environment.

----------------------------------------------------------------------
${NC}"

# Waiting for container to be ready
sleep 2

# Entering Omnia-core container
ssh localhost -p 2222
