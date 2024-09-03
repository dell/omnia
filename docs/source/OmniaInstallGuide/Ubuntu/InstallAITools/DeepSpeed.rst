Setup DeepSpeed
=================

DeepSpeed is a deep learning optimization library developed by Microsoft, designed to make training large-scale machine learning models more efficient and scalable. It provides several key features that help accelerate training and reduce the resource requirements for training state-of-the-art models.

Prerequisites
--------------

Before deploying a DeepSpeed MPIJob, the following prerequisites must be fulfilled:

1. Kubeflow must be deployed on all the cluster nodes. `Click here <kubeflow.html>`_ to know more about deploying Kubeflow.

2. Configure the *mpi-operator* package to execute the v2beta1 API. `Click here <mpi_operator_config.html>`_ to know more about this configuration.

3. Verify that the cluster nodes have sufficient allocatable resources for the ``hugepages-2Mi`` and ``Intel Gaudi accelerator``. To check the allocatable resources on all nodes, run: ::

    kubectl describe <node-name> | grep -A 10 "Allocatable"

4. [Optional] If required, you can adjust the resource parameters in the ``ds-configurator.yml`` file based on the availability of resources on the nodes.


Deploy DeepSpeed
-----------------

After you have completed all the prerequisites, do the following to deploy a DeepSpeed MPIJob:

1. Create a namespace to manage all your DeepSpeed workloads. Execute the following command: ::

    kubectl create ns workloads

2. Verify that the namespace has been created by executing the following command: ::

    kubectl get namespace workloads

   *Expected output*: ::

       NAME        STATUS  AGE
       workloads   Active  14s

3. Apply the YAML configuration file for the MPIJob. This file should define the DeepSpeed job using the Kubeflow MPIJob resource as a reference. Execute the following command: ::

    kubectl apply -f example.yml

   *Expected output*: ::

       mpijob.kubeflow.org/gaudi-llm-ds-ft created

4. Check the status of the pods to ensure that the MPIJob is being initialized correctly. Execute the following command to get the pod status: ::

    kubectl get pod -n workloads

   *Expected output (when pods are starting)*: ::

       NAME                             READY  STATUS     RESTARTS  AGE
       gaudi-llm-ds-ft-launcher-zp9mw   0/1    Pending    0         8s
       gaudi-llm-ds-ft-worker-0         0/1    Pending    0         8s

5. After some time (approx 30 minutes), check the status of the pods again to verify if they are up and running. Execute the same command from step 4.

   *Expected output (when pods are running)*: ::

       NAME                             READY  STATUS    RESTARTS  AGE
       gaudi-llm-ds-ft-launcher-zp9mw   1/1    Running   0         33s
       gaudi-llm-ds-ft-worker-0         1/1    Running   0         33s

6. [Optional] If your job requires shared storage, apply the Persistent Volume Claim (PVC) configuration. Execute the following command: ::

    kubectl apply -f pvc.yml

   *Expected output*: ::

       persistentvolumeclaim/shared-model created

7. [Optional] To better understand the MPIJob resource, you can use the following command: ::

    kubectl explain mpijob --api-version=kubeflow.org/v2beta1

   *Expected output*: ::

       GROUP: kubeflow.org
       KIND: MPIJob
       VERSION: v2beta1