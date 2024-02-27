Create local ROCe repository
-----------------------------

.. note:: The ROCe driver is only supported on Ubuntu clusters.

1. Enter the required values in the ``input/software_config.json`` file:

.. csv-table:: Parameters for Software Configuration
   :file: ../../Tables/software_config.csv
   :header-rows: 1
   :keepspace:
   :class: longtable


To install ROCe, include the following line under ``softwares```: ::

        {"name": "bcm_roce", "version": "229.2.9.0"}


For a list of repositories (and their types) configured for ROCe, view the ``input/config/ubuntu/<operating_system_version>/cuda.json`` file. To customize your ROCe installation, update the file. URLs for different versions can be found `here <https://downloads.dell.com>`_: ::

        {
          "bcm_roce": {
            "cluster": [
              {
                "package": "bcm_roce_driver_{{ bcm_roce_version }}",
                "type": "tarball",
                "url": "",
                "path": ""
              }
            ]
          }
        }


.. note:: The only accepted URL for the ROCe driver is from the Dell Driver website.

2. Enter the required values in the ``input/local_repo_config.yml`` file. For parameter information, `click here <index.html>`_.
3. Run the following commands: ::

       cd local_repo
       ansible-playbook local_repo.yml