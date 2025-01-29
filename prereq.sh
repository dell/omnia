#!/bin/bash

# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.
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


# Define color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[34m'
YELLOW='\033[1;33m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Function to get OS information
get_os_info() {
    if [ -f $os_release_data ]; then
        . $os_release_data
        OS_ID=$ID
        # OS_VERSION=$(awk -F= '/VERSION_ID/ {print $2}' $os_release_data)
        OS_VERSION=$VERSION_ID
        echo "Operating System is $OS_ID version $OS_VERSION"
    else
        OS_ID="Unknown"
        OS_VERSION="Unknown"
        echo "Unable to determine OS version."
        return
    fi
}

get_installed_ansible_version() {
    $venv_py -m pip show ansible 2>/dev/null | grep Version | awk '{print $2}'
}

install_ansible() {
    echo "----------------------------------------------------------"
    echo "INSTALLING ANSIBLE $ansible_version IN THE OMNIA VIRTUAL ENVIRONMENT:"
    echo "----------------------------------------------------------"
    $venv_py -m pip install ansible=="$ansible_version" ansible-core=="$ansible_core_version" distlib #--force-reinstall or --ignore-installed is not required
}

disable_selinux() {
    selinux_count="$(grep "^SELINUX=disabled" /etc/selinux/config | wc -l)"
    if [[ $selinux_count == 0 ]]; then
        echo "DISABLING SELINUX:"
        sed -i 's/^SELINUX=.*/SELINUX=disabled/g' /etc/selinux/config
        echo -e "${RED}Reboot Required to take effect${NC}"
        # Move reboot message to the end
        SELINUX_REBOOT_REQUIRED=true
    fi
}

check_python_version_venv() {
    local venv_py_version=$(python --version 2>&1 | awk '{print $2}')
    local venv_major_version=$(echo "$venv_py_version" | cut -d '.' -f 1)
    local venv_minor_version=$(echo "$venv_py_version" | cut -d '.' -f 2)
    echo ""
    if [ "$venv_major_version" == "$py_major_version" ] && [ "$venv_minor_version" == "$py_minor_version" ]; then
        echo "Python version $venv_py_version matches the required version $py_major_version.$py_minor_version."
    else
        echo "Python version $venv_py_version does not match the required version $py_major_version.$py_minor_version."
        exit 1
    fi
}

compare_and_copy_config() {
    local input_config="$1"
    local example_config="$2"

    # Try to extract cluster_os_type from the input file
    local input_os_type
    local jq_output
    jq_output=$(jq -r '.cluster_os_type' "$input_config" 2>&1)

    if [[ $? -ne 0 ]]; then
        echo -e "${RED}Error: Failed to parse ${YELLOW}${input_config}${NC}"
        echo -e "Below is the error details:"
        echo -e "${RED}${jq_output}${NC}"
        echo ""
        echo -e "${RED}Please check software_config.json for syntax errors and correct them.${NC}"
        echo -e "${RED}After correcting, please rerun ${YELLOW}prereq.sh${NC}"
        exit 1
    else
        input_os_type="$jq_output"
    fi

    # Check against OS_ID
    if [[ "$input_os_type" == "$OS_ID" ]]; then
        echo -e "${GREEN}Existing software_config.json matches the current OS type. No changes made.${NC}"
    else
        echo -e "${RED}Updating software_config.json to match the current OS type and version.${NC}"
        copy_config "$input_config" "$example_config"
    fi
}

# Separate function for copying from examples
copy_config() {
    local input_config="$1"
    local example_config="$2"

    if [[ -f "$example_config" ]]; then
        copy_output=$(cp -v "$example_config" "$input_config")
        echo -e "${GREEN}${copy_output}${NC}"
        echo ""
        echo -e "${RED}Updating cluster_os_version: $OS_VERSION${NC}"
        sed -i "s/\"cluster_os_version\": .*/\"cluster_os_version\": \"$OS_VERSION\",/" "$input_config"

    else
        echo -e "${RED}Error: Example configuration file for $OS_ID not found.${NC}"
        exit 1
    fi
}

# Default settings
ansible_version="9.5.1"
ansible_core_version="2.16.13"
python_version="3.11"
py_major_version="3"
py_minor_version="11"
venv_py=python$python_version
os_release_data="/etc/os-release"
venv_location="/opt/omnia/omnia17_venv" # Do not give a trailing slash
unsupported_os=false
os_type="rhel"
SELINUX_REBOOT_REQUIRED=false

# Start
get_os_info

if [[ "$OS_ID" == "rhel" || "$OS_ID" == "rocky" ]]; then
    os_type="rhel"
    max_val=8.8
    if awk "BEGIN { exit !($OS_VERSION < $max_val) }"; then
	unsupported_os=true
    fi
fi

if [[ "$OS_ID" == "ubuntu" ]]; then
    os_type="ubuntu"
    max_val=20.04
    if awk "BEGIN { exit !($OS_VERSION < $max_val) }"; then
	unsupported_os=true
    fi
fi

if [ "$unsupported_os" = true ]; then
	echo "Unsupported OS for Omnia v1.7 software stack. Creating venv for Omnia v1.6.1 software stack."
	ansible_version="7.7.0"
 	ansible_core_version="2.14.12"
	python_version="39" # RHEL-8.8 onwards and ubuntu-20.04 onwards this is '3.9'
	py_major_version="3"
	py_minor_version="9"
	venv_py=python3.9
	venv_location="/opt/omnia/omnia161_venv" # Do not give a trailing slash
fi

# Check if the OS version is unsupported and print a warning message
install_omnia_version=$(grep "omnia_version:" ".metadata/omnia_version" | cut -d ':' -f 2 | tr -d ' ')
if [[ "$OS_ID" == "rhel" || "$OS_ID" == "rocky" ]]; then
    if [[ "$VERSION_ID" != "8.8" ]]; then
        echo -e "Warning: Running Omnia $install_omnia_version on an unsupported OS ${OS_ID} ${VERSION_ID} may lead to failures in subsequent playbooks. To prevent such issues, please use a supported OS ${OS_ID} 8.8 ."
    fi
elif [[ "$OS_ID" == "ubuntu" ]]; then
   if [ -e /var/log/installer/media-info ]; then
       media_info=$(cat /var/log/installer/media-info)
       if [[ ! $media_info == *"Ubuntu-Server"* ]]; then
       	    echo -e "${YELLOW}Warning: Omnia supports only server edition of Ubuntu. Running Omnia on a non-server edition of Ubuntu may lead to failures in subsequent playbooks.
To prevent such issues, please use the Server edition of Ubuntu.${NC}"
       fi
   fi
   if [[ "$VERSION_ID" != "22.04" ]]; then
     echo -e "Warning: Running Omnia $install_omnia_version on an unsupported OS ${OS_ID} ${VERSION_ID} may lead to failures in subsequent playbooks. To prevent such issues, please use a supported OS ${OS_ID} 22.04 ."
   fi
else
    echo "WARNING: Unsupported OS ${OS_ID}"
fi

# Check if already is a different activated venv
if [ -n "$VIRTUAL_ENV" ]; then
    if [ "$VIRTUAL_ENV" != "$venv_location" ]; then
        echo "Currently activated virtual environment: $VIRTUAL_ENV is not the Omnia virtual environment"
        echo "Please deactivate this virtual environment, then run './prereq.sh'."
        exit 1
    fi
fi

[ -d /opt/omnia ] || mkdir /opt/omnia
[ -d $venv_location ] || mkdir $venv_location
[ -d /var/log/omnia ] || mkdir /var/log/omnia

if [[ "$OS_ID" == "rocky" ]]; then
  echo "------------------------"
  echo "INSTALLING EPEL RELEASE:"
  echo "------------------------"
  dnf install epel-release -y
fi

allow_unauth_apt=""
echo ""
if command -v $venv_py >/dev/null 2>&1; then
    echo "Python $python_version is already installed"
else
    echo "Python $python_version is not installed"
    echo "----------------------"
    echo "INSTALLING PYTHON $python_version:"
    echo "----------------------"
    if [[ "$OS_ID" == "ubuntu" ]]; then
        echo "Operating System: $OS_ID"
        apt install software-properties-common -y
        apt-add-repository ppa:deadsnakes/ppa -y
    	if [ $? -eq 0 ]; then
            echo "Added repo successfully with GPG key"
	else
            check_ubuntu22="$(cat $os_release_data | grep 'VERSION_ID="22.04"' | wc -l)"
            check_ubuntu20="$(cat $os_release_data | grep 'VERSION_ID="20.04"' | wc -l)"
	    allow_unauth_apt="--allow-unauthenticated" 
            if [[ "$check_ubuntu22" == "1" ]]; then
               echo "Adding repo for jammy $OS_ID $OS_VERSION"
               echo "deb [trusted=yes] http://ppa.launchpad.net/deadsnakes/ppa/ubuntu jammy main" > /etc/apt/sources.list.d/deadsnakes-ppa.list
            elif [[ "$check_ubuntu20" == "1" ]]; then
               echo "Adding repo for focal $OS_ID $OS_VERSION"
               echo "deb [trusted=yes] http://ppa.launchpad.net/deadsnakes/ppa/ubuntu focal main" > /etc/apt/sources.list.d/deadsnakes-ppa.list
            fi
	fi
        apt update
        apt install python$python_version -y $allow_unauth_apt
    else
        echo "Operating System: $OS_ID"
        dnf install python$python_version -y
    fi
fi

if ! command -v $venv_py >/dev/null 2>&1; then
    echo "$venv_py installation failed !!"
    exit 1
fi

echo ""
# install the other packages
if [[ "$OS_ID" == "ubuntu" ]]; then
    echo "Installing apt packages for - $OS_ID"
    apt update
    apt install python$python_version-dev python$python_version-venv -y $allow_unauth_apt
    apt install git git-lfs jq -y $allow_unauth_apt
    git lfs pull
else
    echo "Installing dnf packages for - $OS_ID"
    dnf install python$python_version-pip python$python_version-devel -y
    dnf install git-lfs jq -y
    git lfs pull
    disable_selinux
fi

echo ""
# Check if activated venv location equal to the venv_location
if [ "$VIRTUAL_ENV" != "$venv_location" ]; then
    echo "Omnia virtual environment not activated in $venv_location"
    if [ ! -f "$venv_location/bin/activate" ]; then
       $venv_py -m venv $venv_location --prompt omnia17
    fi
    echo "Activating the Omnia virtual environment .."
    source $venv_location/bin/activate

    if [ "$VIRTUAL_ENV" == "$venv_location" ]; then
        echo "Omnia virtual environment activated successfully at $venv_location"
    else
        echo "Failed to activate virtual environment."
        echo "Please manually activate the virtual environment at $venv_location
and install the required package ansible-$ansible_version via pip,
before executing playbooks in Omnia Infrastructure Manager"
        exit 1
    fi
else
    echo "Virtual environment already activated at $venv_location"
fi
echo ""
echo "Making required changes to virtual environment at $VIRTUAL_ENV"

check_python_version_venv

# Upgrade pip
echo ""
echo "Upgrading pip in Omnia virtual environment:"
$venv_py -m ensurepip --upgrade
$venv_py -m pip install --upgrade pip

INSTALLED_VERSION=$(get_installed_ansible_version)
echo ""
if [ "$INSTALLED_VERSION" == "$ansible_version" ]; then
    echo -e "${GREEN}Ansible $ansible_version is already installed.${NC}"
else
    echo -e "${RED}Ansible $ansible_version is not installed.${NC}"
    install_ansible
fi

echo "----------------------------------------------------"
echo "Installing collections in Omnia virtual environment:"
echo "----------------------------------------------------"

max_retries=3
retry_count=0
venv_collection_req_file="requirements_collections.yml"
if [ "$unsupported_os" = true ]; then
    echo "Unsupported OS: Installing collections in omnia v1.6.1 venv"
    venv_collection_req_file="upgrade/roles/upgrade_oim/files/requirements_venv161.yml"
fi
while [ $retry_count -lt $max_retries ]; do
    ansible-galaxy collection install -r $venv_collection_req_file
    if [ $? -eq 0 ]; then
        echo "Ansible collections installed successfully"
        break
    else
        echo "Ansible collections installation failed. Retrying in 5 seconds..."
        sleep 5
        retry_count=$((retry_count + 1))
    fi
done

if [ $retry_count -eq $max_retries ]; then
    echo "Ansible collections installation failed after $max_retries retries"
    exit 1
fi


echo "------------------------------"
echo "UPDATING SOFTWARE_CONFIG.JSON:"
echo "------------------------------"
echo "system_os: $OS_ID"
echo "os_version: $OS_VERSION"
dir_path=$(dirname "$(realpath "$BASH_SOURCE")")
echo "Omnia Directory Path: $dir_path"

# Input software_config.json path
input_file="$dir_path/input/software_config.json"

# Determine which example file to use based on OS
example_file="$dir_path/examples/${OS_ID}_software_config.json"

# Ensure the input file exists
if [[ ! -f "$input_file" ]]; then
    echo -e "${RED}No existing software_config.json found. Copying from example file.${NC}"
    copy_config "$input_file" "$example_file"
else
    compare_and_copy_config "$input_file" "$example_file"
fi

echo "--------------------------------------"
echo "INSTALLING OMNIA VIRTUAL ENVIRONMENT:"
echo "--------------------------------------"

touch $venv_location/.omnia

echo -e "${GREEN}"
echo -e "The Omnia virtual environment has been setup now.
This virtual environment can be activated using the command
${YELLOW}'source $venv_location/bin/activate'${GREEN}
All the Omnia playbooks should be run from the activated Omnia virtual environment"
echo -e "${NC}"

# Show SELinux reboot message if necessary
if [[ "$SELINUX_REBOOT_REQUIRED" == "true" ]]; then
    echo -e "${RED}"
    echo "SELinux has been successfully disabled. Please reboot the system before proceeding. However, if you are upgrading or restoring the Omnia Infrastructure Manager, avoid rebooting to prevent the loss of telemetry data."
    echo -e "${NC}"
fi

echo -e "${BLUE}"
echo "Download the ISO file required to provision in the Omnia Infrastructure Manager."
echo ""
echo "Please configure all the NICs and set the hostname for the Omnia Infrastructure Manager in the format hostname.domain_name. Eg: oimnode.omnia.test"
echo ""
echo "Once IP and hostname is set, provide inputs in input/local_repo_config.yml & input/software_config.json and execute the playbook local_repo/local_repo.yml to created offline repositories."
echo ""
echo "After local_repo.yml execution, to provision the nodes user can provide inputs in input/network_spec.yml, input/provision_config.yml & input/provision_config_credentials.yml and execute the playbook discovery_provision.yml"
echo ""
echo -e "For more information: ${MAGENTA}https://omnia-doc.readthedocs.io/en/latest/"
echo -e "${NC}"
