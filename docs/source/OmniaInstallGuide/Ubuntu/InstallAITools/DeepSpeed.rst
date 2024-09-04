Setup DeepSpeed
=================

DeepSpeed is a deep learning optimization library developed by Microsoft, designed to make training large-scale machine learning models more efficient and scalable. It provides several key features that help accelerate training and reduce the resource requirements for training state-of-the-art models.

Prerequisites
--------------

Before deploying a DeepSpeed MPIJob, the following prerequisites must be fulfilled:

1. Kubeflow must be deployed on all the cluster nodes. `Click here <kubeflow.html>`_ to know more about deploying Kubeflow.

2. Configure the *mpi-operator* package to execute the v2beta1 API. `Click here <mpi_operator_config.html>`_ to know more about this configuration.

3. Verify that the cluster nodes have sufficient allocatable resources for the ``hugepages-2Mi`` and ``Intel Gaudi accelerator``. To check the allocatable resources on all nodes, run: ::

    kubectl describe <intel-gaudi-node-name> | grep -A 10 "Allocatable"

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

3. Open the ``ds_configuration.yml`` file present in the ``examples`` folder and modify the parameters for the DeepSpeed MPIJob. This file defines the DeepSpeed job using the Kubeflow job resource as a reference. After making modifications to the file, you have two options. First, you can directly copy the file to your ``kube_control_plane``. Alternatively, you can create a new blank ``<name>.yml`` file and copy the modified contents to the new file, and then place it on your ``kube_control_plane``. Finally, apply the file using the following command: ::

    kubectl apply -f <filename>.yml

   *Expected output*: ::

       mpijob.kubeflow.org/gaudi-llm-ds-ft created

4. Apply the Persistent Volume Claim (PVC) configuration, required to access shared storage. Execute the following command: ::

    kubectl apply -f pvc.yml

   *Expected output*: ::

       persistentvolumeclaim/shared-model created

5. Check the status of the pods to ensure that the MPIJob is being initialized correctly. Execute the following command to get the pod status: ::

    kubectl get pod -n workloads

   *Expected output (when pods are starting)*: ::

       NAME                             READY  STATUS     RESTARTS  AGE
       gaudi-llm-ds-ft-launcher-zp9mw   0/1    Pending    0         8s
       gaudi-llm-ds-ft-worker-0         0/1    Pending    0         8s

6. After some time (approx 30 minutes), check the status of the pods again to verify if they are up and running. Execute the same command from step 4.

   *Expected output (when pods are running)*: ::

       NAME                             READY  STATUS    RESTARTS  AGE
       gaudi-llm-ds-ft-launcher-zp9mw   1/1    Running   0         33s
       gaudi-llm-ds-ft-worker-0         1/1    Running   0         33s

7. [Optional] To better understand the MPIJob resource, you can use the following command: ::

    kubectl explain mpijob --api-version=kubeflow.org/v2beta1

   *Expected output*: ::

       GROUP: kubeflow.org
       KIND: MPIJob
       VERSION: v2beta1

*Final output*:

Once DeepSpeed deployment is complete, the following output is displayed while checking the status of the pods using the ``kubectl get pod -n workloads`` command:

.. image:: ../../../images/DeepSpeed.png