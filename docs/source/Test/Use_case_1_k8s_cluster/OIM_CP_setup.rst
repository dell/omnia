Configure Control Plane (OIM)
===============================

* Identify a node to function as a control plane (CP). Ensure that the node is not part of any existing cluster.
* Check the space requirements for the CP. Add or remove disk space based on the packages that you require. ##provide a link to the space req page##
* Install the supported OS on the CP. ##provide a link to the OS matrix##
* Ensure that the CP has access to the internet.
* Configure the CP NIC.
* Install GIT on the control plane.
* Set the hostname of the CP based on the hostname requirements. ##provide a link to the hostname requirements page##
* Configure the YUM repository on the CP. [Optional: only applicable to RHEL OS]
* Clone the Omnia repository from GitHub onto the CP.
* [Optional] Set up a proxy server for the CP.