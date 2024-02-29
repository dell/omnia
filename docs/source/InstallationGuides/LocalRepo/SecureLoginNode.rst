Create secure login node repository
-----------------------------------


1. Enter the required values in the ``input/software_config.json`` file:

.. csv-table:: Parameters for Software Configuration
   :file: ../../Tables/software_config.csv
   :header-rows: 1
   :keepspace:
   :class: longtable


To install OFED, include the following line under ``softwares```: ::

        {"name": "secure_login_node"},


For a list of repositories (and their types) configured for OFED, view the ``input/config/<operating_system>/<operating_system_version>/secure_login_node.json`` file. To customize your repository installation, update the file.:

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
          "secure_login_node": {
            "cluster": [
              {
              "package": "community.general",
              "type": "ansible_galaxy_collection",
              "version": "4.4.0"
              },
              {
              "package": "install-snoopy",
              "type": "shell",
              "url": "https://github.com/a2o/snoopy/raw/install/install/install-snoopy.sh"
              },
              {"package": "mailx", "type": "rpm", "repo_name": "baseos"},
              {"package": "postfix", "type": "rpm", "repo_name": "baseos"},
              {"package": "gcc", "type": "rpm", "repo_name": "appstream"},
              {"package": "gzip", "type": "rpm", "repo_name": "appstream"},
              {"package": "make", "type": "rpm", "repo_name": "baseos"},
              {"package": "procps-ng", "type": "rpm", "repo_name": "baseos"},
              {"package": "socat", "type": "rpm", "repo_name": "appstream"},
              {"package": "tar", "type": "rpm", "repo_name": "appstream"},
              {"package": "wget", "type": "rpm", "repo_name": "appstream"},
              {"package": "psacct", "type": "rpm", "repo_name": "baseos"},
              {"package": "psacct", "type": "rpm", "repo_name": "baseos"},
              {"package": "python3.9", "type": "rpm", "repo_name": "appstream"}

            ]
          }
        }



2. Enter the required values in the ``input/local_repo_config.yml`` file. For parameter information, `click here <index.html>`_.
3. Run the following commands: ::

       cd local_repo
       ansible-playbook local_repo.yml