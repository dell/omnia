OpenLDAP
--------

1. Enter the required values in the ``input/software_config.json`` file:

.. csv-table:: Parameters for Software Configuration
   :file: ../../Tables/software_config.csv
   :header-rows: 1
   :keepspace:
   :class: longtable


To install OpenLDAP, include the following line under ``softwares```: ::

        {"name": "openldap"},


For a list of repositories (and their types) configured for OpenLDAP, view the ``input/config/<operating_system>/<operating_system_version>/openldap.json`` file. To customize your OpenLDAP installation, update the file.:

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
          "openldap": {
            "cluster": [
              {"package": "openldap-ltb", "type": "rpm", "repo_name": "ldap"},
              {"package": "openldap-ltb-contrib-overlays", "type": "rpm", "repo_name": "ldap"},
              {"package": "openldap-ltb-mdb-utils", "type": "rpm", "repo_name": "ldap"},
              {"package": "libsodium", "type": "rpm", "repo_name": "epel"},
              { "package": "ansible-role-ldaptoolbox-openldap",
                "type": "git",
                "url": "https://github.com/ltb-project/ansible-role-ldaptoolbox-openldap.git",
                "version": "main"
              }
            ]
          }
        }


2. Enter the required values in the ``input/local_repo_config.yml`` file. For parameter information, `click here <index.html>`_.
3. Run the following commands: ::

       cd local_repo
       ansible-playbook local_repo.yml
