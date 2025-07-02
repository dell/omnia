Set up Slurm
==============

**Prerequisites**

* Ensure that ``slurm`` entry is present in the ``softwares`` list in ``software_config.json``, as mentioned below:
  
  ::
    
    "softwares": [
                    {"name": "slurm" },
                 ]

* Ensure that the following sub-group entry is also present in the ``software_config.json`` file: ::

            "slurm": [
                    {"name": "slurm_control_node"},
                    {"name": "slurm_node"},
                    {"name": "login"}
                ]

* Ensure to run ``local_repo.yml`` with the ``slurm`` entry present in ``software_config.json`` to download all required slurm packages.

* Once all the required parameters in `omnia_config.yml <../schedulerinputparams.html#id13>`_ are filled in, ``omnia.yml`` can be used to set up Slurm.

* If ``slurm_installation_type`` is ``nfs_share`` in ``omnia_config.yml``, ensure that ``slurm_share`` is set to ``true`` in `storage_config.yml <../schedulerinputparams.html#id17>`_, for one of the entries in ``nfs_client_params``.


**Inventory details**

* All the applicable inventory groups are ``slurm_control_node``, ``slurm_node``, and ``login``.

* The inventory file must contain:

    1. Exactly 1 ``slurm_control_node``.
    2. At least 1 ``slurm_node``.
    3. At least 1 ``login`` node (Optional).


**Sample inventory**
::

    [slurm_control_node]

    10.5.1.101

    [slurm_node]

    10.5.1.103

    [login]

    10.5.1.105


**Install Slurm**

Run either of the following commands:

    1. ::

            ansible-playbook omnia/omnia.yml -i <inventory filepath>

    2. ::

            ansible-playbook scheduler/scheduler.yml -i <inventory filepath>
    
.. caution:: The ``scheduler.yml`` playbook can be run only after executing ``omnia.yml`` at least once.

.. note:: To add new nodes to an existing cluster, click `here. <../../../Maintenance/addnode.html>`_
