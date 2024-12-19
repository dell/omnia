Step 1: Execute prereq.sh
===========================

Starting from version 1.7, Omnia will be executed within a Python virtual environment. To set up this environment, the ``prereq.sh`` script is utilized. This script installs the necessary Python 3.11, creates the Python virtual environment, as well as installs Ansible 9.5.1 version and other software packages required by Omnia on the OIM. The predefined path for this virtual environment is ``/opt/omnia/omnia17_venv``. This approach ensures that Omnia has the correct dependencies and runs smoothly within a controlled and isolated environment.

.. caution::

    * To run Omnia, it is crucial to use the Python virtual environment created by the ``prereq.sh`` script. Do not delete the virtual environment directory (/opt/omnia/omnia17_venv/) as it is necessary for the proper functioning of Omnia.
    * If you have a proxy server set up for your OIM, you must configure the proxy environment variables on the OIM before running any Omnia playbooks. For more information, `click here <../Setup_CP_proxy.html>`_.
    * Ensure to execute the Omnia playbooks from inside the git cloned Omnia repository folder. Executing the playbooks outside leads to playbook execution failures.

* Use the following command to execute the ``prereq.sh`` script on the OIM: ::

    cd omnia
    ./prereq.sh

* To activate the virtual environment, use the following command: ::

    source /opt/omnia/omnia17_venv/bin/activate

* To verify that the virtual environment is active, check if the following prompt is displayed: ::

    (omnia) [root@<control_plane_name> omnia]#

.. note::
    * Omnia recommends to disable SELinux before proceeding with the installation. If SELinux is not disabled, it will be disabled by the script and the you will be prompted to reboot the OIM.
    * The file ``input/software_config.json`` is overwritten with the default values (based on the operating system) when ``prereq.sh`` is executed.


.. note::

    If you want to deactivate the virtual environment set up by the ``prereq.sh`` script, use the following command from within the activated virtual environment: ::

        deactivate

.. caution:: If you want to delete and recreate the Omnia-created virtual environment, ensure to back up the pip packages before doing so. To backup the packages, run the ``pip freeze >> omnia_venv_pip_reqs.txt`` command from within the activated virtual environment. This command creates a backup file called ``omnia_venv_pip_reqs.txt`` in the current directory. After you have recreated the virtual environment using the ``prereq.sh`` script, restore the pip packages from the activated virtual environment using the ``pip install -r omnia_venv_pip_reqs.txt`` command.

