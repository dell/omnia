Virtual environment
=====================

⦾ **After executing prereq.sh script, why do I see the error displayed below?**

.. image:: ../../../images/virtual_env_1.png
    :width: 600pt

**Potential Cause**: The virtual environment created by the ``prereq.sh`` script is not activated. The activation of the virtual environment is completely user-driven.

**Resolution**:

* Executing ``./prereq.sh`` installs all the packages and sets up the virtual environment - but doesn't activate it. You can activate the Python virtual environment using the following command: ::

    source /opt/omnia17_venv/bin/activate

 .. image:: ../../../images/virtual_env_2.png


* To verify that the virtual environment is active, check if the following prompt is displayed: ::

    (omnia) [root@<control_plane_name> omnia]#


⦾ **While executing any Omnia playbook, why do I encounter a "No such file or directory" or "Install ansible" error?**

**Potential Cause**: Ansible is not installed on the control plane server.

**Resolution**: Ansible is mandatory for Omnia's functionality. Use the ``prereq.sh`` script to install set up the Omnia virtual environment and install Ansible on the control plane. For more information, `click here <../../../OmniaInstallGuide/Ubuntu/Prereq.sh/index.html>`_.