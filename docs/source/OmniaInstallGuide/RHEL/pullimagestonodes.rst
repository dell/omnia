Download custom packages/images to the cluster
===============================================

**Download packages/images to the control plane registry**

To download packages/images to the control plane registry/repository, ``local_repo.yml`` should be executed.

Follow the steps below to download packages/images:

    1. Create a ``.json`` file with all the required packages/images. For example, ``custom_image.json``.

    2. Updated ``custom_image.json`` with the package/image information. Follow the sample template added below:

        ::

            {
              "custom_image": {
                "cluster": [
                  {
                    "package": "quay.io/jetstack/cert-manager-controller",
                    "tag": "v1.13.0",
                    "type": "image"
                  },
                  {
                    "package": "quay.io/jetstack/cert-manager-webhook",
                    "tag": "v1.13.0",
                    "type": "image"
                  },
                  {
                    "package": "nfs-common",
                    "type": "deb",
                    "repo_name": "jammy"
                  },
                ]
              }
            }

    3. Enter custom_image entry in ``input/software_config.json``.

        ::

            {"name": "custom_image"}

    4. Enter the required softwares in ``software_config.json`` for which ``<software_name>.json`` file is created, based on the OS type and version running on the cluster. For example,

        ::

            {
                "cluster_os_type": "ubuntu",
                "cluster_os_version": "22.04",
                "repo_config": "partial",
                "softwares": [
                    {"name": "custom_image"},
                ]
            }

    3. Execute the following command to download required images from internet to control plane:

        ::

            cd local_repo
            ansible-playbook local_repo.yml

    .. note:: If user registry is required to be used, ensure to update the registry details in ``input/local_repo_config.yml`` before executing ``local_repo.yml``. For example, ``user_registry: - { host: 192.168.0.1:5001, cert_path: "/home/ca.crt" }``.

**Pull images/packages to the cluster**

    1. Create an inventory file (for example, ``imagepull_inventory.ini``) with the required groups. Assign the required nodes to each group. Images will be pulled to the nodes within these groups. For example, if you have a Kubernetes cluster, then the inventory file should contain ``kube_control_plane`` and ``kube_node`` groups. An inventory example is provided below:

        ::

            inventory.ini
            [kube_control_plane]
            10.8.0.1

            [kube_node]
            10.8.0.2
            10.8.0.3

    2. Execute the following command to pull images from control plane to the desired nodes:

        ::

            cd utils
            ansible-playbook pull_images_to_nodes.yml -i imagepull_inventory.ini

.. note:: Since the nodes are behind the proxy, they don't have direct internet access. Only the control plane has direct access to the public internet.
          Nodes can connect to the internet via the control plane by setting the ``http_proxy`` and ``https_proxy`` environment variables, in the following format: ::

              export http_proxy=http://<Host IP address of control plane>:3128
              export https_proxy=http://<Host IP address of control plane>:3128

          Example: ::

              export http_proxy=http://10.5.255.254:3128
              export https_proxy=http://10.5.255.254:3128

          To pull any specific image to a particular node, do the following:

              1. Connect to the node via SSH protocol and configuring the ``http_proxy`` and ``https_proxy`` environment variables by following the above commands.
              2. Use the following command to pull any desired image:

                    ::

                        nerdctl pull <image_name>