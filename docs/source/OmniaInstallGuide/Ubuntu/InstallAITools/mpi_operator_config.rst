MPI-Operator configuration for DeepSpeed deployment
=======================================================

While deploying Kubernetes on a cluster, Omnia sets the *mpi-operator* API version set to ``v2beta1``. But if you choose to deploy Kubeflow on that same Kubernetes cluster, the *mpi-operator* API version automatically changes to ``v1``.
You can install ``v2beta1`` for better performance when compared to ``v1``.

In order to configure Kubeflow with *mpi-operator* API version v2beta1, execute the following command: ::

    cd tools
    ansible-playbook configure_mpi_operator.yml -i <kubeflow inventory> --tags mpiv2beta1

*Expected output*: The v1 mpi-operator and the training operator of Kubeflow is uninstalled.

[Optional] If you want to revert back to the default configuration, execute the following command: ::

    cd tools
    ansible-playbook configure_mpi_operator.yml -i <kubeflow inventory> --tags mpiv1

*Expected output*: The mpijob.kubeflow.org (v2beta1) is uninstalled, and v1 mpi-operator along with the training operator of Kubeflow is installed.