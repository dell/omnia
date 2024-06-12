Install Kubernetes
===================

**Prerequisites**

* Ensure that ``k8s`` entry is present in the ``softwares`` list in ``software_config.json``, as mentioned below:
    ::

        "softwares": [
                        {"name": "k8s", "version":"1.26.12"},
                     ]

* Ensure to run ``local_repo.yml`` with the ``k8s`` entry present in ``software_config.json``, to download all required Kubernetes packages and images.

* Once all the required parameters in `omnia_config.yml <schedulerinputparams.html#id11>`_ are filled in, ``omnia.yml`` can be used to set up Kubernetes.

* Ensure that ``k8s_share`` is set to ``true`` in `storage_config.yml <schedulerinputparams.html#id16>`_, for one of the entries in ``nfs_client_params``.

**Inventory details**

* For Kubernetes, all the applicable inventory groups are ``kube_control_plane``, ``kube_node``, and ``etcd``.

* The inventory file must contain:

    1. Exactly 1 ``kube_control_plane``.
    2. At least 1 ``kube_node``.
    3. Odd number of ``etcd`` nodes.

**Sample inventory**
::

    [kube_control_plane]

    10.5.1.101

    [kube_node]

    10.5.1.102

    [etcd]

    10.5.1.101

.. note:: If an additional NIC other than admin NIC is present on the cluster, inventory should be updated with argument ``ip``, and ``ip`` should have the value of required admin IP in case node has more than one network interface. If ``kube_control_plane`` has 2 interfaces ``eno1`` and ``eno2`` with IPs ``eno1=10.5.0.3`` and ``eno2=198.168.0.19``, inventory should have the following format: ::

    [kube_control_plane]
    10.5.0.3 ip=10.5.0.3
    [kube_node]
    10.5.0.4 ip=10.5.0.4
    [etcd]
    10.5.0.3 ip=10.5.0.3

**To install Kubernetes**

Run either of the following commands:

    1. ::

            ansible-playbook omnia.yml -i inventory

    2. ::

            ansible-playbook scheduler.yml -i inventory

.. note:: To add new nodes to an existing cluster, click `here. <../addinganewnode.html>`_

**Additional installations**

Omnia installs the following packages on top of the Kubernetes stack:

1.	*amdgpu-device-plugin (ROCm device plugin)*

    This is a Kubernetes device plugin implementation that enables the registration of AMD GPU in a container cluster for compute workload.
    Click `here <https://github.com/ROCm/k8s-device-plugin>`_ for more information.

2.	*mpi-operator*

    The MPI Operator makes it easy to run allreduce-style distributed training on Kubernetes.
    Click `here <https://github.com/kubeflow/mpi-operator>`_ for more information.

3.	*xilinx device plugin*

    The Xilinx FPGA device plugin for Kubernetes is a Daemonset deployed on the Kubernetes (k8s) cluster which allows you to:

        i.	Discover the FPGAs inserted in each node of the cluster and expose information about FPGA such as number of FPGA, Shell (Target Platform) type and etc.

        ii.	Run FPGA accessible containers in the k8s cluster

    Click `here <https://github.com/Xilinx/FPGA_as_a_Service/tree/master/k8s-device-plugin>`_ for more information.

4.	*nfs-client-provisioner*

    * NFS subdir external provisioner is an automatic provisioner that use your existing and already configured NFS server to support dynamic provisioning of Kubernetes Persistent Volumes via Persistent Volume Claims.
    * The NFS server utilised here is the one mentioned in ``storage_config.yml``.
    * Server IP is ``<nfs_client_params.server_ip>`` and path is ``<nfs_client_params>.<server_share_path>`` of the entry where ``k8s_share`` is set to ``true``.

    Click `here <https://github.com/kubernetes-sigs/nfs-subdir-external-provisioner>`_ for more information.

5.	*nvidia-device-plugin*

    The NVIDIA device plugin for Kubernetes is a Daemonset that allows you to automatically:

        i.	Expose the number of GPUs on each nodes of your cluster
        ii.	Keep track of the health of your GPUs
        iii. Run GPU enabled containers in your Kubernetes cluster.

    Click `here <https://github.com/NVIDIA/k8s-device-plugin>`_ for more information.

**Additional configurations for nvidia-device-plugin**

After executing ``scheduler.yml`` or ``omnia.yml``, there are some manual steps which user needs to perform for the NVIDIA device plugin to detect GPU on the nodes.

    * First, install "nvidia-container-toolkit" from `this link <https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html>`_. This must be installed on servers running NVIDIA GPUs.
    * As per the `nvidia-container-toolkit installation guide <https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html>`_, follow the below steps based on the OS running on your cluster.

        **Steps for RHEL/Rocky Linux**

        1.	Check the values of http_proxy and https_proxy environment variables from ``/opt/omnia/offline/local_repo_access.yml`` on the control plane.
        2.	SSH to node with the NVIDIA GPU and set http_proxy environment variables.
        3.	Execute the following command:
            ::

                curl -s -L https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | \
                sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo

        4.	Execute the following command:
            ::

                sudo yum install -y nvidia-container-toolkit

        5.	Execute the following command:
            ::

                sudo nvidia-ctk runtime configure --runtime=containerd

        6.	Execute the following command:
            ::

                systemctl restart containerd

        7.  Execute the following command:
            ::

                rm -rf /etc/yum.repos.d/nvidia-container-toolkit.repo


        **Steps for Ubuntu**

        1.	Check http_proxy and https_proxy values from ``/opt/omnia/offline/local_repo_access.yml`` on ControlPlane.
        2.	SSH to node with GPU and set http proxy environment variables.
        3.	Execute the following command:
            ::

                curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
                && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
                sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
                sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

        4.	Execute the following command:
            ::

               sudo apt-get update

        5.	Execute the following command:
            ::

                sudo apt-get install -y nvidia-container-toolkit

        6.	Execute the following command:
            ::

                sudo nvidia-ctk runtime configure --runtime=containerd

        7.	Execute the following command:
            ::

                systemctl restart containerd

        8.  Execute the following command:
            ::

                rm -rf /etc/apt/sources.list.d/nvidia-container-toolkit.list


**Optional installation**

In addition to the above mentioned plugins, user can also install the *kubernetes device plugin for RoCE NIC*. For complete installation steps, `click here <k8s_plugin_roce_nic.html>`_.