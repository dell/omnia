Create FreeIPA repository
-------------------------

1. Enter the required values in the ``input/software_config.json`` file:

.. csv-table:: Parameters for Software Configuration
   :file: ../../Tables/software_config.csv
   :header-rows: 1
   :keepspace:
   :class: longtable


To install FreeIPA, include the following line under ``softwares```: ::

        {"name": "freeipa"},


For a list of repositories (and their types) configured for FreeIPA, view the ``input/config/<operating_system>/<operating_system_version>/freeipa.json`` file. To customize your FreeIPA installation, update the file.:

For Ubuntu: ::

        {
            "ofed": {
              "cluster": [
                { "package": "freeipa",
                  "type": "iso",
                  "url": "https://content.mellanox.com/ofed/MLNX_OFED-24.01-0.3.3.1/MLNX_OFED_LINUX-24.01-0.3.3.1-ubuntu20.04-x86_64.iso",
                  "path": ""
                }
              ]
            }
        }


For RHEL or Rocky: ::

        {
            "freeipa": {
                "cluster": [
                    {"package": "bind", "type": "rpm", "repo_name": "appstream"},
                    {"package": "ipa-server-dns", "type": "rpm", "repo_name": "appstream"},
                    {"package": "ipa-server", "type": "rpm", "repo_name": "appstream"},
                    {"package": "bind-utils", "type": "rpm", "repo_name": "appstream"},
                    {"package": "ipa-client", "type": "rpm", "repo_name": "appstream"},
                    {"package": "ipa-admintools", "type": "rpm", "repo_name": "appstream"},
                    {"package": "idm:DL1", "type": "module", "repo_name": "appstream"},
                    {"package": "idm:DL1/{dns,adtrust}", "type": "module", "repo_name": "appstream"},
                    {"package": "idm:DL1/client", "type": "module", "repo_name": "appstream"}
                ]
            }
        }


2. Enter the required values in the ``input/local_repo_config.yml`` file. For parameter information, `click here <index.html>`_.
3. Run the following commands: ::

       cd local_repo
       ansible-playbook local_repo.yml
