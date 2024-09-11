vLLM enablement for clusters containing Intel Gaudi accelerators
===================================================================

Prerequisites
--------------

Before enabling the vLLM capabilities of the cluster running Intel Gaudi accelerators, the following prerequisites must be fulfilled:

1. Verify that the cluster nodes have sufficient allocatable resources for the ``hugepages-2Mi`` and ``Intel Gaudi accelerator``. To check the allocatable resources on all nodes, run: ::

    kubectl describe <intel-gaudi-node-name> | grep -A 10 "Allocatable"

2. [Optional] If required, you can adjust the resource parameters in the ``vllm_configuration.yml`` file based on the availability of resources on the nodes.


Deploy vLLM (Intel)
----------------------

After you have completed all the prerequisites, do the following to deploy vLLM on a cluster running with Intel Gaudi accelerators:

1. Create a namespace to manage on your ``kube_control_plane`` according to the details provided in ``vllm_configuration.yml`` file. Execute the following command: ::

    kubectl create ns workloads

2. Verify that the namespace has been created by executing the following command: ::

    kubectl get namespace workloads

   *Expected output*: ::

       NAME        STATUS  AGE
       workloads   Active  45s

3. To create a configuration file for vLLM deployment, follow these steps:

    a. Locate the ``vllm_configuration.yml`` file in the ``examples/ai_examples/vllm`` folder.
    b. Open the ``vllm_configuration.yml`` file.
    c. Add the necessary details such as Hugging Face token, and allocated resources for the vLLM deployment.
    d. After modifying the file, you have two choices:

        - Directly copy the modified file to your ``kube_control_plane``.
        - Create a new blank ``<vLLM_configuration_filename>.yml`` file, paste the modified contents into it, and save it on your ``kube_control_plane``.

    e. Finally, apply the file using the following command: ::

        kubectl apply -f <vLLM_configuration_filename>.yml

   *Expected output*: ::

       service/vllm-llama-svc created
       deployment.apps/vllm-llama created

4. To create and apply the Persistent Volume Claim (PVC) configuration file, required to access shared storage, follow these steps:

    a. Create a new blank ``<PVC_filename>.yml`` file,
    b. Paste the following content into it, and save it on your ``kube_control_plane``. ::

        apiVersion: v1
        kind: PersistentVolumeClaim
        metadata:
          name: shared-model
          namespace: workloads
        spec:
          storageClassName: nfs-client
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: <storage-size>

    c. Add the necessary details such as name, namespace, and storage size for the vLLM deployment. Use the same configurations as provided in the ``<vLLM_configuration_filename>.yml`` file.
    d. Finally, apply the file using the following command: ::

        kubectl apply -f <PVC_filename>.yml

   *Expected output*: ::

       persistentvolumeclaim/shared-model created

5. Verify the PVC is bound and available for the deployment using the following command: ::

    kubectl get pvc -n workloads

   *Expected output*: ::

       NAME          STATUS  VOLUME                                     CAPACITY  ACCESS MODES  STORAGECLASS  AGE
       shared-model  Bound   pvc-0a066bce-9511-4f73-ac41-957a8088cfb0   400Gi     RWX           nfs-client    14s

6. After some time, check the status of the pods again to verify if they are up and running. Execute the following command to get the pod status: ::

    kubectl get pod -n workloads

   *Expected output (when pods are running)*: ::

       NAME                             READY  STATUS    RESTARTS  AGE
       vllm-llama-669bbf5c9b-1h7jm      1/1    Running   0         58s

6. After approximately 30 minutes, verify the service status of the vLLM deployment using the following command: ::

    kubectl get svc -n workloads

   *Expected output*: ::

       NAME            TYPE       CLUSTER-IP     EXTERNAL-IP  PORT(S)          AGE
       vllm-llama-svc  NodePort   10.233.13.108  <none>       8000:32195/TCP   71s

7. Finally, verify the endpoints using the following command: ::

    kubectl get endpoints vllm-llama-svc -n workloads

   *Expected output*: ::

       NAME             ENDPOINTS               AGE
       vllm-llama-svc   10.233.108.196:8000     82s

*Final output*:

Once vLLM deployment is complete, the following output is displayed while executing the ``curl -X POST -d "param1=value1&param2=value2" <Intel_node_IP>:<port>`` command.