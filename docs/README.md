# Omnia
Omnia (Latin: all or everything) is a deployment tool to turn Dell EMC PowerEdge servers with standard RPM-based Linux OS images into a functioning Slurm/Kubernetes cluster. Omnia is a collection of [Ansible](https://ansible.org) playbooks for installing and configuring Slurm or Kubernetes on an inventory of servers, along with additional software packages and services.

## Installing Omnia
Omnia requires that servers already have an RPM-based Linux OS running on them, and are all connected to the Internet. Currently all Omnia testing is done on [CentOS](https://centos.org). Please see [PREINSTALL](PREINSTALL.md) for instructions on network setup.

Once servers have functioning OS and networking, you can using Omnia to install and start Slurm and/or Kubernetes. Please see [INSTALL](INSTALL.md) for instructions.

## Contributing to Omnia
The Omnia project was started to give members of the [Dell Technologies HPC Community](https://dellhpc.org) a way to easily setup clusters of Dell EMC servers, but to contribute useful tools, fixes, and functionality back to the HPC Community.

### Open to All
While we started Omnia within the Dell Technologies HPC Community, that doesn't mean that it's limited to Dell EMC servers, networking, and storage. This is an open project, and we want to encourage *everyone* to use and contribute to Omnia!

### Anyone Can Contribute!
It's not just new features and bug fixes that can be contributed to the Omnia project! Anyone should feel comfortable contributing. We are asking for all types of contributions:
* New feature code
* Bug fixes
* Documentation updates
* Feature suggestions
* Feedback
* Validation that it works for your particular configuration

If you would like to contribute, see [CONTRIBUTING](https://github.com/dellhpc/omnia/blob/master/CONTRIBUTING.md).
