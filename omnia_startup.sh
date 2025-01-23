#!/bin/bash


# This script is used to generate the Omnia core docker image.
# The image is based on Fedora and uses systemd to start all of the necessary
# services.
#
# This script prompts the user for the persistent volume path and the root
# password. It then checks if the persistent volume path exists.
#
# The script checks if the ssh key file exists. If it does not exist, a new ssh


# Print prompt for the persistent volume path
echo "Please provide Omnia shared path:"

# Prompt the user for the persistent volume path.
read -p "Enter: " omnia_path

# Check if the persistent volume path exists.
if [ ! -d "$omnia_path" ]; then
    echo "Omnia shared path does not exist!"
    exit
fi


# Print prompt for the root password
echo "Please provide root password:"

# Prompt the user for the root password.
read -p "Enter: " -s passwd


# Print prompt for the root password confirmation
echo "Please confirm password:"

# Prompt the user for the root password confirmation.
read -s -p "Enter: " cnf_passwd

# Check if the provided passwords match.
if [ "$passwd" != "$cnf_passwd" ]; then
    echo "Invalid root password, passwords do not match!"
    exit 1
fi

hashed_passwd=$(openssl passwd -1 $passwd)

# Print message if the ssh key file exists.
ssh_key_file="/root/.ssh/id_rsa"

if [ -f "$ssh_key_file" ]; then
    echo "Skipping generating new ssh key pair."
else
    echo "Generating a new ssh key pair."
    ssh-keygen -q -N '' -f /root/.ssh/id_rsa
fi


# Create the ssh configuration directory if it does not exist.
echo "Creating the ssh configuration directory if it does not exist."
mkdir -p "$omnia_path/omnia/ssh_config/.ssh"
# Copy the ssh private key to the omnia shared path.
echo "Copying the ssh private key to the omnia shared path."
cp $ssh_key_file "$omnia_path/omnia/ssh_config/.ssh/id_rsa"

# Copy the ssh public key to the omnia shared path.
echo "Copying the ssh public key to the omnia shared path."
cp $ssh_key_file.pub "$omnia_path/omnia/ssh_config/.ssh/id_rsa.pub"

# Get the ssh public key.
ssh_public_key="$(cat /root/.ssh/id_rsa.pub)"


# Print message if the ssh public key is already in the authorized_keys.
if grep -q "$ssh_public_key" ~/.ssh/authorized_keys; then
    echo "Skipping adding ssh public key to the authorized_keys."
else
    echo "Adding ssh public key to the authorized_keys."
    echo "$ssh_public_key" >> ~/.ssh/authorized_keys
fi


# Check if the hostname is configured with a domain name.
if hostname | grep -q '\.'; then
    echo "Hostname is configured with a domain name."
else
    echo "Invalid hostname, hostname is not configured with a domain name!"
    exit 1
fi


# Print message for creating the ssh_config directory in Omnia shared path.
echo "Creating the ssh_config directory in Omnia shared path."
mkdir -p "$omnia_path/omnia/ssh_config/.ssh"


# Print message for building the Omnia core docker image.
echo "Building the Omnia core docker image."
podman build -t omnia_core:latest -f omnia_core


# Print message for running the Omnia core docker image.
echo "Running the Omnia core docker image."
podman run -dt --hostname omnia_core --restart=always --security-opt label:disable -v /opt/omnia:/opt/omnia -v /opt/omnia/ssh_config/.ssh:/root/.ssh:z -e ROOT_PASSWORD_HASH=$passwd --net=host --name omnia_core --cap-add=CAP_AUDIT_WRITE --replace omnia_core:latest

oim_metadata_file="$omnia_path/omnia/oim_metadata"

if [ ! -f "$oim_metadata_file" ]; then
    echo "Creating oim_metadata file"
    {
        echo "oim_crt: \"podman\""
        echo "oim_shared_path: $omnia_path"
        echo "omnia_version: 2.0.0.0"
    } >> "$oim_metadata_file"
fi


