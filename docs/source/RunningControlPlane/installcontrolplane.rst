Running Control Plane Playbook
==============================


1. On the control plane, change the working directory to the directory where you want to clone the Omnia Git repository.

2. Clone the Omnia repository using the command: ::

    git clone https://github.com/dellhpc/omnia.git


3. Change the directory to ``omnia`` using the command ::

    cd omnia

5. Change the directory to ``omnia/input`` using the command ::

    cd input_params

6. Edit the *provision.yml* file to update the required variables.

.. warning:: The IP address *192.168.25.x* is used for PowerVault Storage communications. Therefore, do not use this IP address for other configurations.

7. Provided that the ``host_mapping_file_path`` is updated as per the provided template, Omnia deploys the control plane and assigns the component roles by executing the ``omnia.yml`` file.  To deploy the Omnia control plane, run the following command ::

    ansible-playbook control_plane.yml

8. By running ``control_plane.yml``, the following configurations take place:

    i. All available compute nodes will be PXE booted to have IP addresses and host names as specified in ``omnia/input/provision.yml``.

    ii. All ports required for xCAT to run will be opened (For a complete list, check out the `Security Configuration Document <../SecurityConfigGuide/PortsUsed/xCAT>`_).

    iii. A PostgreSQL database is set up with all relevant cluster information such as MAC IDs, service tags, infiniband IPs, BMC IPs etc.

    iv. Offline repositories will be created based on the OS being deployed across the cluster.

.. note:: If the cluster does not have access to the internet, AppStream will not function. Please use the available offline repositories instead.

.. warning:: Once xCAT is installed, restart your SSH session to the control plane to ensure that the newly set up environment variables come into effect.