Role based additional software installation
============================================

Apart from the packages listed in the ``/opt/omnia/input/project_default/software_config.json`` file, additional software can also be installed on the cluster nodes. You can do so in two following ways: 

1. To install additional packages during provisioning, you need to follow the below steps:

    * First, fill up the ``additional_software.json`` and ``software_config.json`` input files.
    * Then, execute the ``local_repo.yml`` playbook in order to download the required packages.
    * Finally, execute the ``discover_and_provision.yml`` playbook in order to provision the cluster nodes along with the new additional software packages.

2. To install packages after the cluster is up and running, the ``software_update.yml`` utility playbook can be leveraged separately.

Prerequisites
---------------

* Download the required packages to the Pulp container using the ``local_repo.yml`` playbook.
* Ensure that the ``opt/omnia/input/project_default/roles_config.yml`` input file has been updated with the desired roles for the nodes.
* Ensure that the target cluster nodes are in ``booted`` state.
* Add the following entry under the ``softwares`` section in ``/opt/omnia/input/project_default/software_config.json``: ::
    
    "softwares": [ 
               
               {“name”: “additional_software”} 
            
            ]

Steps
-------

1. Create a ``additional_software.json`` file under ``input/config/<cluster_os_type>/<cluster_os_version>`` directory, with all the additional packages listed. These packages will be installed on the cluster nodes.

2. Provide details about the software installation requirements for each group or role in the ``/opt/omnia/input/project_default/software_config.json`` file. Use the format of subgroups, where each subgroup name is a comma-separated list of group or role names.

    * Specify the **role** in order to install the desired packages on all the nodes linked to a specific role. 
        
        **Example**: In the below example, the packages will be installed on all the nodes linked to the role ``default`` and ``compiler_node``:
        ::

            "additional_software": [
                
                {"name": "default,compiler_node"}

            ]

    * Specify the **group names** in order to install the desired packages on all the nodes linked to specific groups. 
        
        **Example**: In the below example, the packages will be installed on all the nodes linked to ``grp1`` and ``grp 2``: 
        ::

            "additional_software": [
                
                {"name": "grp1,grp2"}

            ]

    * Specify a combination of **role** and **group names** in order to install the desired packages on a specific group of nodes under a role. 
        
        **Example**: In the below example, the packages will be installed on all the nodes linked to ``grp2`` of the ``default`` role: 
        ::

            "additional_software": [
                
                {"name": "default,grp2"}

            ]

.. note:: If no roles or groups are specified, the packages will be installed on all the nodes.

Input parameters
-----------------

Enter the following parameters in ``input/config/<cluster_os_type>/<cluster_os_version>/additional_software.json``:

.. csv-table:: additional_software.json
    :file: ../Tables/additional_software.csv
    :header-rows: 1
    :keepspace:


Sample of ``additional_software.json``
----------------------------------------

The below provided sample contains all the possible combinations for roles and groups in the ``additional_software.json``:

::

    {
        "additional_software": {

	        "cluster": [
	            {
		            "package": "quay.io/jetstack/cert-manager-controller",
		            "type": "image",
                    "tag": "v1.13.0"
                },
                    
                {
                    "package": "nfs-utils",
                    "type": "rpm",
                    "repo_name": "baseos"
                }
            ]

        }, 
            
        "default,compiler_node": {
        
            "cluster": [
                {
                    "package_list": ["python3-PyMySQL", "apr-util", "asciidoc"],
                    "type": "rpm_list",
                    "repo_name": "appstream",
                    "reboot_required": true
                }
            ]
        }
    }


Playbook execution
--------------------

Run the playbook using the following command: ::

    cd utils/software_update
    ansible-playbook software_update.yml

