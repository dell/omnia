Update all local repositories
===============================

This playbook updates the repository configurations on compute nodes by creating ``.repo`` files. It should be used when:

* New **user repositories** are added in ``input/local_repo_config.yml``
* New **Omnia repositories** are added in ``input/local_repo_config.yml``
* **Versioned software** such as ``amdgpu``, ``beegfs``, or ``rocm`` is added in ``input/software_config.json``

.. note:: After adding a new repository or software entry, first run the ``local_repo.yml`` playbook. Then, run this playbook to propagate the changes to all compute nodes.

Playbook execution
-------------------

To execute the playbook: ::

    ssh omnia_core
    cd /omnia/utils
    ansible-playbook update_user_repo.yml -i <inventory_filepath>
 
*<inventory_filepath> refers to the path of the Kubernetes or Slurm inventory.*