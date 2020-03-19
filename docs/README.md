# Omnia Documentation
Omnia (Latin: all or everything) is a deployment tool to turn Dell EMC PowerEdge servers with standard RPM-based Linux OS images into a functioning Slurm/Kubernetes cluster. Omnia is a collection of [Ansible](https://ansible.org) playbooks for installing and configuring Slurm or Kubernetes on an inventory of servers, along with additional software packages and services.

## Installing Omnia
Omnia requires that servers already have an RPM-based Linux OS running on them, and are all connected to the Internet. Currently all Omnia testing is done on [CentOS](https://centos.org). Please see [PREINSTALL](PREINSTALL.md) for instructions on network setup.

Once servers have functioning OS and networking, you can using Omnia to install and start Slurm and/or Kubernetes. Please see [INSTALL](INSTALL.md) for instructions.

## Contributing to Omnia
The Omnia project was started to give members of the [Dell Technologies HPC Community](https://dellhpc.org) a way to easily setup clusters of Dell EMC servers, but to contribute useful tools, fixes, and functionality back to the HPC Community.
