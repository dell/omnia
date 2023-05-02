Airgap
-----

* The airgap role will help create offline repositories on control plane which all the compute nodes will access. This will remove the overhead of subscribing all the compute nodes to RHEL.
* Currently, ``airgap.yml`` only updates RHEL repositories.

``airgap.yml`` runs based on the following parameters in ``input/provision_config.yml``:

+--------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Parameter          | Details                                                                                                                                                                                                             |
+====================+=====================================================================================================================================================================================================================+
| update_repos       | Indicates whether airgap.yml will update offline RHEL repos.                                                                                                                                                        |
|      ``boolean``   |                                                                                                                                                                                                                     |
|      Required      |      Choices:                                                                                                                                                                                                       |
|                    |                                                                                                                                                                                                                     |
|                    |      * ``false`` <- Default                                                                                                                                                                                         |
|                    |                                                                                                                                                                                                                     |
|                    |      * ``true``                                                                                                                                                                                                     |
+--------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| rhel_repo_path     | * For RHEL control planes with   no subscription available, users are required to add a list of repositories   to be maintained offline. Currently, it is recommended to download AppStream,   BaseOS and CRB only. |
|      ``JSON list`` |      * Ensure ``repo_url``  and   ``repo_name`` are provided.                                                                                                                                                       |
|      Optional      |                                                                                                                                                                                                                     |
|                    |                                                                                                                                                                                                                     |
|                    |      **Default value**: ::                                                                                                                                                                                          |
|                    |                                                                                                                                                                                                                     |
|                    |      	- { repo: "AppStream", repo_url: "", repo_name:   "" }                                                                                                                                                     |
|                    |      	                                                                                                                                                                                                           |
|                    |      	- { repo: "BaseOS", repo_url: "", repo_name:   "" }                                                                                                                                                        |
|                    |      	                                                                                                                                                                                                           |
|                    |      	- { repo: "CRB", repo_url: "", repo_name: ""   }                                                                                                                                                           |
|                    |                                                                                                                                                                                                                     |
+--------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+


``airgap.yml`` is internally called when ``provision.yml`` is executed.
Alternatively, run the following commands: ::

    cd airgap
    ansible-playbook airgap.yml



