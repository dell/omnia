Running Control Plane Playbook
==============================


1. On the control plane, change the working directory to the directory where you want to clone the Omnia Git repository.
2. Clone the Omnia repository using the command: ::

    git clone https://github.com/dellhpc/omnia.git


3. Change the directory to **omnia** using the command: ``cd omnia``
4. Edit the *omnia_config.yml* file to:
    * Specify the Kubernetes version which will be installed on the manager and compute nodes in the **k8s_version** variable. By default, it is set to **1.16.7**. Edit this variable to change the version. Supported versions are 1.16.7 and 1.19.3.
    * To configure a login node in the cluster. By default, the *login_node_required* variable is set to "true". Using the login node, cluster administrators can provide access to users to log in to the login node to schedule Slurm jobs. However, if you do not want to configure the login node, then you can set the variable to "false". Without the login node, Slurm jobs can be scheduled only through the manager node.

.. note::
    * Ensure that the parameter ``enable_security_support`` in ``telemetry\input_params\base_vars.yml`` is set to 'false' before editing the following variables.

    * The login node will be configured when running ``omnia.yml``.

    * To enable security features on the Control Plane, use the steps provided `here <security/index.html>`_.

    * To deploy Grafana on the Control Plane, use the steps provided `here <../Telemetry_Visualization/index.html>`_.

    * Supported values for Kubernetes CNI are calico and flannel. The default value of CNI considered by Omnia is calico.

    * The default value of `Kubernetes Pod <https://docs.projectcalico.org/getting-started/kubernetes/quickstart>`_ Network CIDR is 10.244.0.0/16. If 10.244.0.0/16 is already in use within your network, select a different Pod Network CIDR.

    * The default path of the Ansible configuration file is ``/etc/ansible/``. If the file is not present in the default path, then edit the ``ansible_conf_file_path`` variable to update the configuration path.

    * If you choose to enable security on the login node, simply follow the steps mentioned `here <../RunningControlPlane/security/loginnode.html>`_.



5. Change the directory to ``control_plane/input_params`` using the command: ``cd omnia/control_plane/input_params``

6. Edit the *base_vars.yml* file to update the required variables.

.. note:: The IP address *192.168.25.x* is used for PowerVault Storage communications. Therefore, do not use this IP address for other configurations.



7. Provided that the host_mapping_file_path is updated as per the provided template, Omnia deploys the control plane and assigns the component roles by executing the ``omnia.yml`` file.  To deploy the Omnia control plane, run the following command: ``ansible-playbook control_plane.yml``



8. If the host_mapping_file_path is not provided, then you must manually assign the component roles through the AWX UI.



Omnia creates a log file which is available at: ``/var/log/omnia_control_plane.log``.
