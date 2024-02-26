Create local CUDA repository
-----------------------------

1. Enter the required values in the ``input/software_config.json`` file:

.. csv-table:: Parameters for Software Configuration
   :file: ../../Tables/software_config.csv
   :header-rows: 1
   :keepspace:
   :class: longtable


To install CUDA, include the following line under ``softwares```: ::

        {"name": "cuda", "version": "12.3.2"},


For a list of repositories (and their types) configured for CUDA, view the ``input/config/<operating_system>/<operating_system_version>/cuda.json`` file. To customize your CUDA installation, update the file. URLs for different versions can be found `here <https://developer.nvidia.com/cuda-downloads>`_: ::

        {
          "cuda": {
            "cluster": [
              { "package": "cuda",
                "type": "iso",
                "url": "https://developer.download.nvidia.com/compute/cuda/12.3.2/local_installers/cuda-repo-rhel8-12-3-local-12.3.2_545.23.08-1.x86_64.rpm",
                "path": ""
              },
              { "package": "dkms",
                "type": "rpm",
                "repo_name": "epel"
              }
            ]
          }
        }


.. note:: If the target cluster runs on RHEL, ensure the "dkms" package is included in ``input/config/rhel/8.x/cuda.json`` as illustrated above.

2. Enter the required values in the ``input/local_repo_config.yml`` file. For parameter information, `click here <index.html>`_.
3. Run the following commands: ::

       cd local_repo
       ansible-playbook local_repo.yml