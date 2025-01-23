Containerized HPC benchmark execution
--------------------------------------

Use this playbook to download docker images and pull images onto cluster nodes using `apptainer <https://apptainer.org/docs/user/main/index.html/>`_.

1. Ensure that the cluster has been `provisioned by the provision tool. <../../InstallationGuides/InstallingProvisionTool/index.html>`_ and the `cluster has been set up using omnia.yml. <../../InstallationGuides/BuildingClusters/index.html>`_

2. Enter the following variables in ``utils/hpc_apptainer_job_execution/hpc_apptainer_job_execution_config.yml``:

+-------------------------+-----------------------------------------------------------------------------------------------------------+
| Parameter               | Details                                                                                                   |
+=========================+===========================================================================================================+
| **hpc_apptainer_image** | * Docker image details to be downloaded in to cluster nodes using apptainer to create a sif file.         |
| ``JSON list``           |                                                                                                           |
| Required                | * Example (for single image): ::                                                                          |
|                         |                                                                                                           |
|                         |                                                                                                           |
|                         | 	hpc_apptainer_image:                                                                                  |
|                         | 	                                                                                                      |
|                         | 	- { image_url: "docker.io/intel/oneapi-hpckit:latest" }                                               |
|                         |                                                                                                           |
|                         | * Example (for multiple images): ::                                                                       |
|                         |                                                                                                           |
|                         |     hpc_apptainer_image:                                                                                  |
|                         |                                                                                                           |
|                         |        - { image_url: "docker.io/intel/oneapi-hpckit:latest" }                                            |
|                         |                                                                                                           |
|                         |        - { image_url: "docker.io/tensorflow/tensorflow:latest" }                                          |
|                         |                                                                                                           |
|                         | * If provided, docker credentials in ``omnia_config.yml``, it will be used for downloading docker images. |
|                         |                                                                                                           |
+-------------------------+-----------------------------------------------------------------------------------------------------------+
| **hpc_apptainer_path**  | * Directory to filepath for storing apptainer sif files on cluster nodes.                                 |
|                         |                                                                                                           |
| ``string``              | * It is recommended to use a directory inside a shared path that is accessible to all cluster nodes.      |
|                         |                                                                                                           |
| Required                | * **Default value:** ``"/home/omnia-share/softwares/apptainer"``                                          |
+-------------------------+-----------------------------------------------------------------------------------------------------------+

To run the playbook: ::

    cd utils/hpc_apptainer_job_execution

    ansible-playbook hpc_apptainer_job_execution.yml -i inventory

.. note:: Use the inventory file format specified under `Sample Files. <../../samplefiles.html>`_

HPC apptainer jobs can be initiated on a slurm cluster using the following sample command: ::

    srun -N 3 --mpi=pmi2 --ntasks=4 apptainer run /home/omnia-share/softwares/apptainer/oneapi-hpckit_latest.sif hostname

