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

ansible_version="9.5.1"
python_version="3.11"
py_major_version="3"
py_minor_version="11"
venv_py=python$python_version
os_release_data="/etc/os-release"
venv_location="/opt/omnia17_venv" # Do not give a trailing slash

# Function to get OS information
get_os_info() {
    if [ -f $os_release_data ]; then
        . $os_release_data
        OS_ID=$ID
        OS_VERSION=$(awk -F= '/VERSION_ID/ {print $2}' $os_release_data)
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
    $venv_py -m pip install ansible=="$ansible_version" #--force-reinstall or --ignore-installed is not required
}

disable_selinux() {
    selinux_count="$(grep "^SELINUX=disabled" /etc/selinux/config | wc -l)"
    if [[ $selinux_count == 0 ]]; then
        echo "DISABLING SELINUX:"
        sed -i 's/^SELINUX=.*/SELINUX=disabled/g' /etc/selinux/config
        echo "SELinux is disabled. Reboot system to notice the change in status before executing playbooks in control plane!!"
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

# Check if already is a different activated venv
if [ -n "$VIRTUAL_ENV" ]; then
    if [ "$VIRTUAL_ENV" != "$venv_location" ]; then
        echo "Currently activated virtual environment: $VIRTUAL_ENV is not the Omnia virtual environment"
        echo "Please deactivate this virtual environment, then run './prereq.sh'."
        exit 1   
    fi
fi

# Start
get_os_info

[ -d $venv_location ] || mkdir $venv_location
[ -d /opt/omnia ] || mkdir /opt/omnia
[ -d /var/log/omnia ] || mkdir /var/log/omnia

if [[ "$OS_ID" == "rocky" ]]; then
  echo "------------------------"
  echo "INSTALLING EPEL RELEASE:"
  echo "------------------------"
  dnf install epel-release -y
fi

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
        check_ubuntu22="$(cat $os_release_data | grep 'VERSION_ID="22.04"' | wc -l)"
        check_ubuntu20="$(cat $os_release_data | grep 'VERSION_ID="20.04"' | wc -l)"
        if [[ "$check_ubuntu22" == "1" ]]; then
            echo "Adding repo for $OS_ID $OS_VERSION" 
            echo "deb [trusted=yes] http://ppa.launchpad.net/deadsnakes/ppa/ubuntu jammy main" > /etc/apt/sources.list.d/deadsnakes-ppa.list
        elif [[ "$check_ubuntu20" == "1" ]]; then
            echo "Adding repo for $OS_ID $OS_VERSION" 
            echo "deb [trusted=yes] http://ppa.launchpad.net/deadsnakes/ppa/ubuntu focal main" > /etc/apt/sources.list.d/deadsnakes-ppa.list
        else
            apt-add-repository ppa:deadsnakes/ppa -y
        fi
        apt update
        apt install python$python_version -y
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
    apt install python$python_version-dev python$python_version-venv -y
    apt install git git-lfs -y
    git lfs pull
else
    echo "Installing dnf packages for - $OS_ID"
    dnf install python$python_version-pip python$python_version-devel -y
    dnf install git-lfs -y
    git lfs pull
    disable_selinux
fi

echo ""
# Check if activated venv location equal to the venv_location
if [ "$VIRTUAL_ENV" != "$venv_location" ]; then
    echo "Omnia virtual environment not activated in $venv_location"
    if [ ! -f "$venv_location/bin/activate" ]; then
       $venv_py -m venv $venv_location --prompt omnia
    fi
    echo "Activating the Omnia virtual environment .."
    source $venv_location/bin/activate
    
    if [ "$VIRTUAL_ENV" == "$venv_location" ]; then
        echo "Omnia virtual environment activated successfully at $venv_location"
    else
        echo "Failed to activate virtual environment."
        echo "Please manually activate the virtual environment at $venv_location
and install the required package ansible-$ansible_version via pip,
before executing playbooks in control plane"
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
    echo "Ansible $ansible_version is already installed."
else
    echo "Ansible $ansible_version is not installed."
    install_ansible
fi

echo "------------------------------"
echo "UPDATING SOFTWARE_CONFIG.JSON:"
echo "------------------------------"
echo "system_os: $OS_ID"
echo "os_version: $OS_VERSION"
dir_path=$(dirname "$(realpath "$BASH_SOURCE")")
echo "Omnia Directory Path: $dir_path"
if [[ "$OS_ID" == 'ubuntu' ]]; then
    cp -v "$dir_path/examples/ubuntu_software_config.json" "$dir_path/input/software_config.json"
elif [[ "$OS_ID" == 'rhel' ]]; then
    cp -v "$dir_path/examples/rhel_software_config.json" "$dir_path/input/software_config.json"
elif [[ "$OS_ID" == 'rocky' ]]; then
    cp -v "$dir_path/examples/rocky_software_config.json" "$dir_path/input/software_config.json"
fi

echo ""
echo "Updating software_config.json with cluster_os_version: $OS_VERSION"
sed -i "s/\"cluster_os_version\": .*/\"cluster_os_version\": $OS_VERSION,/" "$dir_path/input/software_config.json"

touch $venv_location/.omnia

echo ""
echo "The Omnia virtual environment has been setup now.
This virtual environment can be activated using the command
'source $venv_location/bin/activate'
All the Omnia playbooks should be run from the activated Omnia virtual environment"

echo ""
echo "Download the ISO file required to provision in the control plane."
echo ""
echo "Please configure all the NICs and set the hostname for the control plane in the format hostname.domain_name. Eg: controlplane.omnia.test"
echo ""
echo "Once IP and hostname is set, provide inputs in input/local_repo_config.yml & input/software_config.json and execute the playbook local_repo/local_repo.yml to created offline repositories."
echo ""
echo "After local_repo.yml execution, to provision the nodes user can provide inputs in input/network_spec.yml, input/provision_config.yml & input/provision_config_credentials.yml and execute the playbook discovery_provision.yml"
echo ""
echo "For more information: https://omnia-doc.readthedocs.io/en/latest/InstallationGuides/InstallingProvisionTool/index.html"
