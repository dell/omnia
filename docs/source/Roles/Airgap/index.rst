Offline repositories for the  cluster
=====================================

* The airgap feature will help create offline repositories on control plane which all the cluster  nodes will access. This will remove the overhead of subscribing all the cluster  nodes to RHEL.
* Currently, ``airgap.yml`` only updates RHEL repositories.

``airgap.yml`` runs based on the following parameters in ``input/provision_config.yml``:

+------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Parameter                          | Details                                                                                                                                                                   |
+====================================+===========================================================================================================================================================================+
| **update_repos**                   | * Indicates whether ``provision.yml`` will   update offline RHEL repos (applicable from the second run of ``provision.yml``)                                              |
|                                    |                                                                                                                                                                           |
|                                    | * In the first execution of ``provision.yml``, Omnia updates the BaseOS,   Appstream and CRB repos.                                                                       |
|                                    |                                                                                                                                                                           |
|                                    | * If ``update_repos``: false, none of the repos required for cluster  nodes   will be updated provided the repos are already available.                                   |
| ``boolean``                        |                                                                                                                                                                           |
|                                    | * If ``update_repos``: true, BaseOS, Appstream and CRB repos created for   cluster  nodes will be updated                                                                 |
|                                    |                                                                                                                                                                           |
|      Required                      | Choices:                                                                                                                                                                  |
|                                    |                                                                                                                                                                           |
|                                    |                                                                                                                                                                           |
|                                    | * ``false`` <- Default                                                                                                                                                    |
|                                    |                                                                                                                                                                           |
|                                    |                                                                                                                                                                           |
|                                    | * ``true``                                                                                                                                                                |
+------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **rhel_repo_alphabetical_folders** | * Indicates whether the packages in the local repos or subscription repos are ordered in alphabetical directories.                                                        |
|                                    |                                                                                                                                                                           |
|                                    | * For RHEL 8, when subscription is activated, this variable should be set to true.                                                                                        |
|                                    |                                                                                                                                                                           |
|                                    |                                                                                                                                                                           |
| ``boolean``                        | Choices:                                                                                                                                                                  |
|                                    |                                                                                                                                                                           |
|                                    |                                                                                                                                                                           |
|      Required                      | * ``false`` <- Default                                                                                                                                                    |
|                                    |                                                                                                                                                                           |
|                                    |                                                                                                                                                                           |
|                                    | * ``true``                                                                                                                                                                |
+------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **rhel_repo_local_path**           | * The repo path and names of the software repository to be configured on the cluster nodes.                                                                               |
|                                    |                                                                                                                                                                           |
|                                    | * Provide the repo data file path, which ends with .repo extension in repo_url parameter.                                                                                 |
|                                    |                                                                                                                                                                           |
|                                    | * Provide a **valid** url for BaseOS and AppStream repositories.                                                                                                          |
| ``JSON list``                      |                                                                                                                                                                           |
|                                    | * This variable should be filled if control plane OS is RHEL and subscription is not activated.                                                                           |
|                                    |                                                                                                                                                                           |
|      Optional                      | * This variable should be filled if the control plane OS is Rocky and the ``provision_os`` is rhel.                                                                       |
|                                    | .. note:: Omnia does not validate the ``repo_url`` provided. Invalid entries will cause ``provision.yml`` to fail.                                                        |
|                                    |                                                                                                                                                                           |
|                                    | Sample value: ::                                                                                                                                                          |
|                                    |                                                                                                                                                                           |
|                                    |                                                                                                                                                                           |
|                                    |       - { repo: "AppStream", repo_url: "http://xx.yy.zz/pub/Distros/RedHat/RHEL8/8.8/RHEL-8-appstream.repo", repo_name: "RHEL-8-appstream-partners" }                     |
|                                    |                                                                                                                                                                           |
|                                    |       - { repo: "BaseOS", repo_url: "http://xx.yy.zz/pub/Distros/RedHat/RHEL8/8.8/RHEL-8-baseos.repo", repo_name: "RHEL-8-baseos-partners" }                              |
|                                    |                                                                                                                                                                           |
+------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------+


``airgap.yml`` is internally called when ``provision.yml`` is executed.
Alternatively, run the following commands: ::

    cd airgap
    ansible-playbook airgap.yml



