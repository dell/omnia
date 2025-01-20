Set up Slurm
==============

.. note:: Omnia supports slurm installation only on RHEL and Rocky Linux (not supported on Ubuntu).

**Prerequisites**

* Ensure that ``slurm`` entry is present in the ``softwares`` list in ``software_config.json``, as mentioned below:
    ::

        "softwares": [
                        {"name": "slurm" },
                     ]

* Ensure to run ``local_repo.yml`` with the ``slurm`` entry present in ``software_config.json``, to download all required slurm packages.

* Once all the required parameters in `omnia_config.yml <../schedulerinputparams.html#id13>`_ are filled in, ``omnia.yml`` can be used to set up Slurm.

* When ``slurm_installation_type`` is ``nfs_share`` in ``omnia_config.yml``, ensure that ``slurm_share`` is set to ``true`` in `storage_config.yml <../schedulerinputparams.html#id17>`_, for one of the entries in ``nfs_client_params``.


**Inventory details**

* For Slurm, all the applicable inventory groups are ``slurm_control_node``, ``slurm_node``, and ``login``.

* The inventory file must contain:

    1. Exactly 1 ``slurm_control_node``.
    2. At least 1 ``slurm_node``.
    3. At least one ``login`` node (Optional).

**Sample inventory**
::

    [slurm_control_node]

    10.5.1.101

    [slurm_node]

    10.5.1.103

    [login]

    10.5.1.105

**To install Slurm**

Run either of the following commands:

    1. ::

            ansible-playbook omnia.yml -i inventory

    2. ::

            ansible-playbook scheduler.yml -i inventory

.. note:: To add new nodes to an existing cluster, click `here. <../../../Maintenance/addnode.html>`_

**Slurm job based user access**

To ensure security while running jobs on the cluster, users can be assigned permissions to access cluster  nodes only while their jobs are running. To enable the feature: ::

    cd scheduler
    ansible-playbook job_based_user_access.yml -i inventory

.. note::

    * The inventory queried in the above command is to be created by the user prior to running ``omnia.yml`` as ``scheduler.yml`` is invoked by ``omnia.yml``

    * Only users added to the 'slurm' group can execute slurm jobs. To add users to the group, use the command: ``usermod -a -G slurm <username>``.
