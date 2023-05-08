Airgap
-----------

* The airgap role will help create offline repositories on control plane which all the compute nodes will access. This will remove the overhead of subscribing all the compute nodes to RHEL.
* Currently, ``airgap.yml`` only updates RHEL repositories.

``airgap.yml`` runs based on the following parameters in ``input/provision_config.yml``:

+--------------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------+
| Parameter                                  | Details                                                                                                                                     |
+============================================+=============================================================================================================================================+
| **update_repos**                           | * Indicates whether ``provision.yml`` will   update offline RHEL repos (applicable from the second run of   ``provision.yml``)              |
|                                            |                                                                                                                                             |
|      ``boolean``                           | * In the first execution of ``provision.yml``, Omnia updates the BaseOS,   Appstream and CRB repos.                                         |
|                                            |                                                                                                                                             |
|      Required                              | * If ``update_repos``: false, none of the repos required for compute nodes   will be updated provided the repos are already available.      |
|                                            |                                                                                                                                             |
|                                            | * If ``update_repos``: true, BaseOS, Appstream and CRB repos created for   compute nodes will be updated                                    |
|                                            |                                                                                                                                             |
|                                            |      Choices:                                                                                                                               |
|                                            |                                                                                                                                             |
|                                            |      ``false`` <- Default                                                                                                                   |
|                                            |                                                                                                                                             |
|                                            |      ``true``                                                                                                                               |
+--------------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------+
|  **rhel_repo_alphabetical_folders**        | * Indicates whether the packages in the local repos or subscription repos are ordered in alphabetical directories.                          |
|                                            |                                                                                                                                             |
|       ``boolean``                          | * For RHEL 8, when subscription is activated, this variable should be set to true.                                                          |
|                                            |                                                                                                                                             |
|       Required                             |                                                                                                                                             |
|                                            |      Choices:                                                                                                                               |
|                                            |                                                                                                                                             |
|                                            |      ``false`` <- Default                                                                                                                   |
|                                            |                                                                                                                                             |
|                                            |      ``true``                                                                                                                               |
+--------------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------+
| **rhel_repo_local_path**                   | * The repo path and names of the software repository to be configured on   the compute nodes.                                               |
|                                            |                                                                                                                                             |
|      ``JSON list``                         | * Provide the repo data file path, which ends with .repo extension in   repo_url parameter.                                                 |
|                                            |                                                                                                                                             |
|      Optional                              | * Provide the url for BaseOS, Appstream and CRB repositories.                                                                               |
|                                            |                                                                                                                                             |
|                                            | * This variable should be filled if control plane OS is RHEL and   subscription is not activated.                                           |
|                                            |                                                                                                                                             |
|                                            | * This variable should be filled if the control plane OS is Rocky and the   ``provision_os`` is rhel.                                       |
|                                            |                                                                                                                                             |
|                                            |      Default value:                                                                                                                         |
|                                            |                                                                                                                                             |
|                                            |      - { repo: “AppStream”, repo_url: “”, repo_name: “” }                                                                                   |
|                                            |                                                                                                                                             |
|                                            |      - { repo: “BaseOS”, repo_url: “”, repo_name: “” }                                                                                      |
|                                            |                                                                                                                                             |
|                                            |      - { repo: “CRB”, repo_url: “”, repo_name: “” }                                                                                         |
+--------------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------+



``airgap.yml`` is internally called when ``provision.yml`` is executed.
Alternatively, run the following commands: ::

    cd airgap
    ansible-playbook airgap.yml



