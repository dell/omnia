Running prereq.sh
=================

``prereq.sh`` is used to verify that all pre-requisites for Omnia are met before running the script.

``cd omnia``

``sh prereqs.sh``


This includes the following checks:

* Stable internet connection

* Operating System: RedHat 8.3 or Rocky 8

* Root (/) and Var (/var) have a minimum of 50% (~35G) free space

* PowerCap policy is disabled

* BIOS system profile is set to 'Performance'

* Root privilege is available

* Python 3.8 will be installed (if not installed).

.. note:: To deploy Omnia, Python provides bindings to system tools such as RPM, DNF, and SELinux.

* PIP will be installed (if not installed).

* Ansible 2.12.9 is installed (if not installed).

* SeLinux will be disabled (if not disabled previously).

.. note::
    * If SeLinux is not disabled, it will be disabled by the script and the user will be prompted to reboot the control plane.
    * If provisioning via IB NICs is required, users are required to install IB drivers using ``yum groupinstall "Infiniband Support" -y``




