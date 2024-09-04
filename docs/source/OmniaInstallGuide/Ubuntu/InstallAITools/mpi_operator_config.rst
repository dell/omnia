MPI-Operator configuration for DeepSpeed deployment
=======================================================

While deploying Kubernetes on a cluster, Omnia sets the *mpi-operator* API version set to ``v2beta1``. But if you choose to deploy Kubeflow on that same Kubernetes cluster, the *mpi-operator* API version automatically changes to ``v1``.

In order to configure Kubeflow with *mpi-operator* API version v2beta1, execute the following command: ::

    cd tools
    ansible-playbook configure_mpi_operator.yml -i <kubeflow inventory> --tags mpiv2beta1

*Expected result*: The mpi-operator API version v1 and the training operator of Kubeflow is uninstalled. The mpi-operator API version v2beta1 is installed.

[Optional] Revert back to the default configuration
------------------------------------------------------

If you want to revert back to the default configuration, execute the following commands step-by-step:

* Step 1: ::

    kubectl delete -f <filename>.yml

   *where <filename>.yml is the YAML configuration file applied to deploy the DeepSpeed MPIJob.*

* Step 2: ::

    kubectl delete -f pvc.yml

* Step 3: ::

    kubectl delete ns workloads

* Step 4: ::

    cd tools
    ansible-playbook configure_mpi_operator.yml -i <kubeflow inventory> --tags mpiv1

*Expected result*:

In the process, the following actions are performed:

* The YAML configuration file used to deploy the DeepSpeed MPIJob is deleted.
* The PVC configuration file is deleted.
* The namespace for DeepSpeed jobs is deleted.
* The mpi-operator API version v2beta1 is uninstalled.
* The mpi-operator API version v1 is installed.
* The training operator of Kubeflow is also installed.