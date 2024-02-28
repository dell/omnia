Create local OFED repository
------------------------------

1. Enter the required values in the ``input/software_config.json`` file:

.. csv-table:: Parameters for Software Configuration
   :file: ../../Tables/software_config.csv
   :header-rows: 1
   :keepspace:
   :class: longtable


To install OFED, include the following line under ``softwares```: ::

        {"name": "ofed", "version": "24.01-0.3.3.1"},


For a list of repositories (and their types) configured for OFED, view the ``input/config/<operating_system>/<operating_system_version>/ofed.json`` file. To customize your OFED installation, update the file.:

For Ubuntu: ::

{
    "ofed": {
      "cluster": [
        { "package": "ofed",
          "type": "iso",
          "url": "https://content.mellanox.com/ofed/MLNX_OFED-24.01-0.3.3.1/MLNX_OFED_LINUX-24.01-0.3.3.1-ubuntu20.04-x86_64.iso",
          "path": ""
        }
      ]
    }
}
For RHEL or Rocky: ::

        {
          "ofed": {
            "cluster": [
              { "package": "ofed",
                "type": "iso",
                "url": "https://content.mellanox.com/ofed/MLNX_OFED-24.01-0.3.3.1/MLNX_OFED_LINUX-24.01-0.3.3.1-rhel8.7-x86_64.iso",
                "path": ""
              }
            ]
          }
        }

.. note::
* If the package version is customized, ensure that the ``version`` value is updated in ``software_config.json```.

2. Enter the required values in the ``input/local_repo_config.yml`` file. For parameter information, `click here <index.html>`_.
3. Run the following commands: ::

       cd local_repo
       ansible-playbook local_repo.yml