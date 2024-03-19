Setup PyTorch
---------------

PyTorch is a popular open-source deep learning framework, renowned for its dynamic computation graph that enhances flexibility and ease of use, making it a preferred choice for researchers and developers. With strong community support, PyTorch facilitates seamless experimentation and rapid prototyping in the field of machine learning.


**Prerequisites**

* Ensure nerdctl is available on all cluster nodes.

* If GPUs are present on the target nodes, install NVidia CUDA (with containerd) or AMD Rocm drivers during provisioning. CPUs do not require any additional drivers.

* Use ``local_repo.yml`` to create an offline PyTorch repository. For more information, `click here. <../../InstallationGuides/LocalRepo/PyTorch.html>`_



    **[Optional]**

    * Ensure the system has enough space.

    * Ensure the passed inventory file includes a ``kube_control_plane`` and a ``kube_node_group`` listing all cluster nodes. `Click here <../../samplefiles.html>`_ for a sample file.

    * Nerdctl does not support mounting directories as devices because it is not a feature of containerd (The runtime that nerdctl uses). Individual files need to be attached while running nerdctl.


**Deploying PyTorch**

1. Change directories to the ``tools`` folder: ::

    cd tools

2. Run the ``pytorch.yml`` playbook: ::

    ansible-playbook pytorch.yml -i inventory

**Accessing PyTorch (CPU)**

1. Verify that the PyTorch image present in container engine images: ::

    nerdctl images

2. Use the container image per your needs: ::

    nerdctl run -it --rm pytorch/pytorch:latest

For more information, `click here <https://hub.docker.com/r/pytorch/pytorch/tags>`_.


**Accessing PyTorch (AMD)**

1. Verify that the PyTorch image present in container engine images: ::

    nerdctl images

2. Use the container image per your needs: ::

    nerdctl run -it --cap-add=SYS_PTRACE --security-opt seccomp=unconfined --device=/dev/kfd --device /dev/dri/card0 --device /dev/dri/card1 --device /dev/dri/card2 --device /dev/dri/renderD128 --device /dev/dri/renderD129  --group-add video --ipc=host --shm-size 8G rocm/pytorch:latest

For more information, `click here <https://rocm.docs.amd.com/projects/install-on-linux/en/develop/how-to/3rd-party/pytorch-install.html>`_.

**Accessing PyTorch (NVidia)**

1. Verify that the PyTorch image present in container engine images: ::

    nerdctl images

2. Use the container image per your needs: ::

    nerdctl  run --gpus all -it --rm nvcr.io/nvidia/pytorch:23.12-py3

For more information, `click here <https://catalog.ngc.nvidia.com/orgs/nvidia/containers/pytorch>`_.
