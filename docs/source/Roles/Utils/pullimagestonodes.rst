Pull images to nodes
=====================

Since the nodes are behind the proxy, they don't have direct internet access. Only the control plane has direct access to the public internet.
Nodes can connect to the internet via the control plane by setting the ``http_proxy`` and ``https_proxy`` environment variables, in the following format: ::

    export http_proxy=http://<Host IP address of control plane>:3128
    export https_proxy=http://<Host IP address of control plane>:3128

Example: ::

    export http_proxy=http://10.5.255.254:3128
    export https_proxy= http://10.5.255.254:3128

**Pull a specific image**

To pull any specific image to a particular node, do the following:

    1. Connect to the node via SSH protocol and configuring the ``http_proxy`` and ``https_proxy`` environment variables by following the above commands.
    2. Use the following command to pull any desired image: ::

        nerdctl pull <image_name>

**Pull multiple images**

To pull multiple images to group of nodes, Omnia provides ``pull_images_to_nodes`` utility.

Below are the steps to pull images using the ``pull_images_to_nodes`` utility:

    1. Enter custom_image entry in ``input/software_config.json``.

        ::

            {"name": "custom_image"}

    2. Enter the required image entries under ``omnia/input/config/<os_type>/<os_version>/custom_image.json``. For example,

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
                  }
                ]
              }
            }

    3. Run the following command to download required images from internet to control plane:

        ::

            ansible-playbook local_repo/local_repo.yml

    4. Create an inventory file (for example, ``imagepull_inventory.ini``) with two groups: ``kube_control_plane`` and ``kube_node``. Assign the required nodes to each group. Images will be pulled to the nodes within these groups.

    5. Run the following command to pull images from control plane to the desired nodes:

        ::

            ansible-playbook utils/pull_images_to_nodes.yml -i imagepull_inventory.ini