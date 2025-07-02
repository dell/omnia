Step 4: Provide all credentials required during Omnia's execution
===================================================================

Omnia provides an additional utility playbook called ``get_config_credentials.yml``. This playbook upon execution creates an input file called ``omnia_config_credentials.yml`` in the ``/opt/omnia/input/project_default`` folder.
In this input file, you can preemptively provide all types of mandatory and optional credentials required by Omnia during its execution. Otherwise, you'll be prompted to enter them during playbook execution.

Prerequisites
---------------

* Ensure that the ``omnia_core`` container is up and running.
* Ensure that the ``opt/omnia/input/project_default/software_config.json`` file is updated with the packages that you want on your cluster.

Task performed by the playbook
---------------------------------

Creates an input file called ``omnia_config_credentials.yml`` in the ``/opt/omnia/input/project_default`` folder.

Execute the playbook
----------------------

To execute the playbook, run the following command: ::

    ssh omnia_core
    cd /omnia/utils/credential_utility
    ansible-playbook get_config_credentials.yml

Things to keep in mind
------------------------

* While executing any Omnia playbook which requires certain credentials, you'll now see a prompt to enter them during playbook execution.
* Credential fields which have the tag ``mandatory`` cannot be left empty. If the ``mandatory`` passwords are not provided or incorrect, the playbook execution will stop and exit while encrypting the credentials file in the background.
* Credential fields which have the tag ``optional`` can be skipped. Even if no input is provided, playbook execution will continue.
* Passwords provided by you will be hidden. You must enter the password for a second time to confirm.
* This utility also supports using tags to provide credentials for specific features or packages. For example, you can use ``--tags provision`` while executing the playbook to only bring up the credentials required to provision the cluster nodes.

Post execution
----------------

After the playbook has been executed, navigate to the ``omnia_config_credentials.yml`` input file is present in the ``/opt/omnia/input/project_default`` folder.
Provide all required credentials for the cluster. See the table below to know more:

.. note:: By default, the ``omnia_config_credentials.yml`` input file is encrypted. Use the below command to decrypt the file: 
    ::
        ansible-vault view omnia_config_credentials.yml --vault-password-file .omnia_config_credentials_key
   
.. csv-table:: Omnia credentials
   :file: ../../Tables/credentials_utility.csv
   :header-rows: 1
   :keepspace:

.. caution:: Once the cluster is up and running, you may only modify the ``bmc_username`` and ``bmc_password`` fields in the ``omnia_config_credentials.yml`` input file. To make these changes, use the command provided below. Do not alter any other fields in the file, as this may lead to unexpected failures.
    ::
        ansible-vault edit omnia_config_credentials.yml --vault-password-file .omnia_config_credentials_key