#!/bin/bash

[ -d /opt/omnia ] || mkdir /opt/omnia
[ -d /var/log/omnia ] || mkdir /var/log/omnia

default_py_version="3.9"
validate_rocky_os="$(cat /etc/os-release | grep 'ID="rocky"' | wc -l)"
validate_ubuntu_os="$(cat /etc/os-release | grep 'ID=ubuntu' | wc -l)"

sys_py_version="$(python3 --version)"
echo "System Python version: $sys_py_version"

if [[ "$validate_rocky_os" == "1" ]];
then
 echo "------------------------"
 echo "INSTALLING EPEL RELEASE:"
 echo "------------------------"
 dnf install epel-release -y
fi

if [[ "$validate_ubuntu_os" == "1" ]];
then
    check_ubuntu22="$(cat /etc/os-release | grep 'VERSION_ID="22.04"' | wc -l)"
    check_ubuntu20="$(cat /etc/os-release | grep 'VERSION_ID="20.04"' | wc -l)"
    if [[ "$check_ubuntu22" == "1" ]]
    then
        echo "deb [trusted=yes] http://ppa.launchpad.net/deadsnakes/ppa/ubuntu jammy main" > /etc/apt/sources.list.d/deadsnakes-ppa.list
    elif [[ "$check_ubuntu20" == "1" ]]
    then
        echo "deb [trusted=yes] http://ppa.launchpad.net/deadsnakes/ppa/ubuntu focal main" > /etc/apt/sources.list.d/deadsnakes-ppa.list
    else
        apt-add-repository ppa:deadsnakes/ppa -y
    fi
    apt update
    echo "----------------------"
    echo "INSTALLING PYTHON 3.9:"
    echo "----------------------"
    apt install python3.9* python3-pip -y
else
    if [[ $(echo $sys_py_version | grep "3.9" | wc -l) != "1" || $(echo $sys_py_version | grep "Python" | wc -l) != "1" ]];
    then
    echo "----------------------"
    echo "INSTALLING PYTHON 3.9:"
    echo "----------------------"
    dnf install python39 -y
    fi
fi
echo "--------------"
echo "UPGRADING PIP:"
echo "--------------"
python3.9 -m pip install --upgrade pip
echo "-------------------"
echo "INSTALLING ANSIBLE:"
echo "-------------------"
executable_path=$(ansible --version 2>/dev/null | awk -F'= ' '/executable location/ {print $2}')
get_os=$(awk -F= '/^ID/{print $2}' /etc/os-release | head -n1)
ansible_status=0
if [[ ! -z "$executable_path" && "$executable_path" = "/usr/bin/ansible" ]]; then
    if [[ "$get_os" == 'ubuntu' ]]; then
        echo "Removing pre-installed ansible && ansible-core packages using apt…"
        ansible_status=1
        sudo apt remove ansible -y
        sudo apt remove ansible-core -y
    elif [[ "$get_os" == '"rhel"' || "$get_os" == '"rocky"' ]]; then
        echo "Removing pre-installed ansible && ansible-core packages using dnf…"
        ansible_status=1
        sudo dnf remove ansible -y
        sudo dnf remove ansible-core -y
    fi

    if ! grep -qxF 'export PATH="/usr/local/bin:$PATH"' ~/.bashrc; then
        echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.bashrc
    fi
fi

installed_ansible_version=$( ansible --version 2>/dev/null | grep -oP 'ansible \[core \K\d+\.\d+' | sed 's/]//')
target_ansible_version="2.14"

if [[ ! -z "$installed_ansible_version" && "$(echo -e "$installed_ansible_version\n$target_ansible_version" | sort -V | tail -n1)" != "$target_ansible_version" ]];
then
    echo "Error: Higher version of Ansible-core ($installed_ansible_version) is already installed. Please uninstall the existing ansible and re-run the prereq.sh again to install $target_ansible_version"
    exit 1
fi

if [[ ! -z "$installed_ansible_version" && "$(echo -e "$installed_ansible_version\n$target_ansible_version" | sort -V | head -n1)" != "$target_ansible_version" ]];
then
    echo "Warning: prereq.sh is uninstalling the existing Ansible-core ($installed_ansible_version) and installing the $target_ansible_version"
fi

python3.9 -m pip install ansible==7.7.0 cryptography==41.0.7
python3.9 -m pip install jinja2==3.1.2

if [[ "$validate_ubuntu_os" == "1" ]];
then
    apt install git git-lfs -y
    git lfs pull
else
    dnf install git-lfs -y
    git lfs pull

    selinux_count="$(grep "^SELINUX=disabled" /etc/selinux/config | wc -l)"
    if [[ $selinux_count == 0 ]];
    then
    echo "------------------"
    echo "DISABLING SELINUX:"
    echo "------------------"
    sed -i 's/^SELINUX=.*/SELINUX=disabled/g' /etc/selinux/config
    echo "SELinux is disabled. Reboot system to notice the change in status before executing playbooks in control plane!!"
    fi
fi

echo "------------------------------"
echo "UPDATING SOFTWARE_CONFIG.JSON:"
echo "------------------------------"
os_version=$(awk -F= '/VERSION_ID/ {print $2}' /etc/os-release)
dir_path=$(dirname "$(realpath "$0")")
echo "system_os: $get_os"
echo "os_version: $os_version"

if [[ "$get_os" == 'ubuntu' ]];
    then
    cp "$dir_path/examples/ubuntu_software_config.json" "$dir_path/input/software_config.json"
    elif [[ "$get_os" == '"rhel"' ]];
    then
    cp "$dir_path/examples/rhel_software_config.json" "$dir_path/input/software_config.json"
    elif [[ "$get_os" == '"rocky"' ]];
    then
    cp "$dir_path/examples/rocky_software_config.json" "$dir_path/input/software_config.json"
fi

sed -i "s/\"cluster_os_version\": .*/\"cluster_os_version\": $os_version,/" "$dir_path/input/software_config.json"

echo ""
echo ""
if [[ "$ansible_status" -eq 1 ]]; then
    echo "IMPORTANT: The pre-installed ansible packages were removed and installed ansible 2.14, user needs to refresh the session to apply changes."
fi
echo ""
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