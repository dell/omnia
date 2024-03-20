Running local repo
------------------

The local repository feature will help create offline repositories on the control plane which all the cluster nodes will access. ``local_repo/local_repo.yml`` runs with inputs from ``input/software_config.json`` and ``input/local_repo_config.yml``:


Run the following commands: ::

    cd local_repo
    ansible-playbook local_repo.yml



**Update local repositories**

This playbook updates all local repositories configured on a provisioned cluster after local repositories have been configured.

To run the playbook: ::

    cd utils
    ansible-playbook update_user_repo.yml -i inventory