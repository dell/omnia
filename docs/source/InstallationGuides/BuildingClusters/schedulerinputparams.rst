Input Parameters for the Cluster
-------------------------------

These parameters are located in ``input/omnia_config.yml``

+--------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Variable                 | Details                                                                                                                                                                    |
+==========================+============================================================================================================================================================================+
| mariadb_password         | * Password used for Slurm database.                                                                                                                                        |
|      ``string``          | * The password must not contain -,\, ',"                                                                                                                                   |
|      Optional            | * The Length of the password should be at least 8.                                                                                                                         |
|                          |                                                                                                                                                                            |
|                          |      **Default values**: ``"password"``                                                                                                                                    |
+--------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| k8s_version              | Kubernetes version.                                                                                                                                                        |
|      ``string``          |                                                                                                                                                                            |
|      Optional            |      Choices:                                                                                                                                                              |
|                          |                                                                                                                                                                            |
|                          |      * ``"1.19.3"``  <-   default                                                                                                                                          |
|                          |      * ``" 1.16.7"``                                                                                                                                                       |
+--------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| k8s_cni                  | Kubernetes SDN network.                                                                                                                                                    |
|      ``string``          |                                                                                                                                                                            |
|      Optional            |      Choices:                                                                                                                                                              |
|                          |                                                                                                                                                                            |
|                          |      * ``"calico"``  <-   default                                                                                                                                          |
|                          |      * ``"flannel"``                                                                                                                                                       |
+--------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| k8s_pod_network_cidr     | * Kubernetes pod network CIDR.                                                                                                                                             |
|      ``string``          | * Make sure this value does not overlap with any of the host   networks.                                                                                                   |
|      Optional            |                                                                                                                                                                            |
|                          |      **Default values**: ``"10.244.0.0/16"``                                                                                                                               |
+--------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| docker_username          | * Username for Dockerhub account                                                                                                                                           |
|      ``string``          | * A kubernetes secret will be created and patched to service account in   default namespace. This kubernetes secret can be used to pull images from   private repositories |
|      Optional            | * This value is optional but suggested avoiding docker pull limit issues                                                                                                   |
+--------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| docker_password          | * Password for Dockerhub account                                                                                                                                           |
|      ``string``          | * This value is mandatory if docker username is provided                                                                                                                   |
|      Optional            |                                                                                                                                                                            |
+--------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ansible_config_file_path | * Path to directory hosting ansible config file (ansible.cfg file)                                                                                                         |
|      ``string``          | * This directory is on the host running ansible, if ansible is installed   using dnf                                                                                       |
|      Optional            | * If ansible is installed using pip, this path should be set                                                                                                               |
|                          |                                                                                                                                                                            |
|                          |      **Default values**: ``/etc/ansible``                                                                                                                                  |
+--------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| login_node_required      | Boolean indicating whether login node is required or not.                                                                                                                  |
|      ``boolean``         |                                                                                                                                                                            |
|      Optional            |      Choices:                                                                                                                                                              |
|                          |                                                                                                                                                                            |
|                          |      * ``false``  <- default                                                                                                                                               |
|                          |      * ``true``                                                                                                                                                            |
+--------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------+