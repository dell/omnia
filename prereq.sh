#!/bin/bash

[ -d /opt/omnia ] || mkdir /opt/omnia
[ -d /var/log/omnia ] || mkdir /var/log/omnia

default_py_version="3.8"
validate_rocky_os="$(cat /etc/os-release | grep 'ID="rocky"' | wc -l)"

sys_py_version="$(python3 --version)"
echo "System Python version: $sys_py_version"

if [[ "$validate_rocky_os" == "1" ]];
then
 echo "------------------------"
 echo "INSTALLING EPEL RELEASE:"
 echo "------------------------"
 dnf install epel-release -y
fi

if [[ $(echo $sys_py_version | grep "3.8" | wc -l) != "1" || $(echo $sys_py_version | grep "Python" | wc -l) != "1" ]];
then
 echo "----------------------"
 echo "INSTALLING PYTHON 3.8:"
 echo "----------------------"
 dnf install python38 -y
fi
echo "--------------"
echo "UPGRADING PIP:"
echo "--------------"
pip3.8 install --upgrade pip
echo "-------------------"
echo "INSTALLING ANSIBLE:"
echo "-------------------"
python3.8 -m pip install ansible==5.10.0
python3.8 -m pip install jinja2==3.1.2

selinux_count="$(grep "^SELINUX=disabled" /etc/selinux/config | wc -l)"
if [[ $selinux_count == 0 ]];
then
 echo "------------------"
 echo "DISABLING SELINUX:"
 echo "------------------"
 sed -i 's/^SELINUX=.*/SELINUX=disabled/g' /etc/selinux/config
 echo "SELinux is disabled. Reboot system to notice the change in status before executing playbooks in control plane!!"
fi
echo ""
echo ""
echo "Please set the hostname for the control plane in the format hostname.domain_name. Eg: controlplane.omnia.test"
echo ""
echo "Once hostname is set, provide inputs in input/provision_config.yml and execute the playbook provision/provision.yml"
echo ""
echo "For more information: https://omnia-doc.readthedocs.io/en/latest/InstallationGuides/InstallingProvisionTool/index.html"