Setup TensorFlow
-----------------

TensorFlow is a widely-used open-source deep learning framework, recognized for its static computation graph that optimizes performance and scalability, making it a favored choice for deploying machine learning models at scale in various industries.

With an Ansible script, deploy TensorFlow on both ``kube_node`` and the ``kube_control_plane``. After the deployment of TensorFlow, you gain access to the TensorFlow container.


**Prerequisites**

* Ensure nerdctl is available on all cluster nodes.

* If GPUs are present on the target nodes, install NVIDIA CUDA (with containerd) or AMD ROCm drivers during provisioning. CPUs do not require any additional drivers.

* Use ``local_repo.yml`` to create an offline TensorFlow repository.

**[Optional prerequisites]**

* Ensure the system has enough space.

* Ensure the inventory file includes a ``kube_control_plane`` and a ``kube_node`` listing all cluster nodes. `Click here <../../samplefiles.html>`_ for a sample file.

* Nerdctl does not support mounting directories as devices because it is not a feature of containerd (runtime that nerdctl uses). Individual files need to be attached while running nerdctl.

* Container Network Interface should be enabled with nerdctl.


**Deploying TensorFlow**

1. Change directories to the ``tools`` folder: ::

    cd tools

2. Run the ``tensorflow.yml`` playbook: ::

    ansible-playbook tensorflow.yml -i inventory

.. note:: During the ``tensorflow.yml`` playbook execution, nodes with AMD or NVIDIA GPUs and drivers will install and test either the ``tensorflow-AMD`` or ``tensorflow-Nvidia`` containers, respectively. If neither GPU type is present with its drivers, it will install and test the ``tensorflow-CPU`` container.

**Accessing TensorFlow (CPU)**

1. Verify that the tensorflow image present in container engine images: ::

    nerdctl images

2. Use the container image per your needs: ::

    nerdctl run -it --rm tensorflow/tensorflow

For more information, `click here <https://www.tensorflow.org/install/docker>`_.


**Accessing TensorFlow (AMD)**

1. Verify that the tensorflow image present in container engine images: ::

    nerdctl images

2. Use the container image per your needs: ::

    nerdctl run -it --network=host --device=/dev/kfd --device /dev/dri/card0 --device /dev/dri/card1 --device /dev/dri/card2 --device /dev/dri/renderD128 --device /dev/dri/renderD129  --ipc=host --shm-size 16G --group-add video --cap-add=SYS_PTRACE --security-opt seccomp=unconfined rocm/tensorflow:latest

For more information, `click here <https://rocm.docs.amd.com/projects/install-on-linux/en/latest/how-to/3rd-party/tensorflow-install.html>`_.

**Accessing TensorFlow (NVIDIA)**

1. Verify that the tensorflow image present in container engine images: ::

    nerdctl images

2. Use the container image per your needs: ::

    nerdctl run --gpus all -it --rm nvcr.io/nvidia/tensorflow:23.12-tf2-py3


For more information, `click here <https://catalog.ngc.nvidia.com/orgs/nvidia/containers/tensorflow>`_.

