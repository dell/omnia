HPC software stack
------------------

Use this playbook to download docker images and pull images onto cluster nodes using apptainer.

1. Ensure that the cluster has been `provisioned by the provision tool. <../../InstallationGuides/InstallingProvisionTool/index.html>`_

2. Enter the following variables in ``utils/hpc_apptainer_job_execution/hpc_apptainer_job_execution_config.yml``:

+-------------------------+-----------------------------------------------------------------------------------------------------------+
| Parameter               | Details                                                                                                   |
+=========================+===========================================================================================================+
| **hpc_apptainer_image** | * Docker image details to be downloaded in to cluster nodes using apptainer to create a sif file.         |
| ``JSON list``           |                                                                                                           |
| Required                | * All sif files will be stored in the ``/root/apptainer`` folder on cluster nodes.                        |
|                         |                                                                                                           |
|                         | * Example (for single image): ::                                                                          |
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
|                         | * **Default value:** ::                                                                                   |
|                         |                                                                                                           |
|                         | 	    hpc_apptainer_image:                                                                              |
|                         | 	                                                                                                      |
|                         | 	    - { image_url: "docker.io/intel/oneapi-hpckit:latest" }                                           |
|                         |                                                                                                           |
+-------------------------+-----------------------------------------------------------------------------------------------------------+

To run the playbook: ::

    cd utils/hpc_apptainer_job_execution

    ansible-playbook hpc_apptainer_job_execution.yml -i inventory

.. note::
    * Use the format specified under `Sample Files <../../samplefiles.html>`_ for inventory.
    * On execution, apptainer sif files will be stored in ``/root/apptainer`` on the cluster nodes.
