Setup Kserve
--------------

Kserve is an open-source serving platform that simplifies the deployment, scaling, and management of machine learning models in production environments, ensuring efficient and reliable inference capabilities. For more information, `click here. <https://kserve.github.io/website/0.11/get_started/>`_ Omnia deploys Kserve (v0.13.0) on the kubernetes cluster. Once Kserve is deployed, any inference service can be installed on the kubernetes cluster.

.. note:: Omnia 1.7 does not support deploying both Kserve and Kubeflow in the same Kubernetes cluster. If Kubeflow is already deployed on the cluster and you wish to deploy Kserve, you must first remove Kubeflow by following the steps `here <kubeflow.html>`_.

.. caution:: Kserve deployment occasionally fails on RHEL 8.8 clusters. `Reprovision the cluster <../../Maintenance/reprovision.html>`_ and re-deploy Kserve. For more information, refer to the `known issues <../../../Troubleshooting/KnownIssues/RHEL/AITools.html>`_ section.

**Prerequisites**

    * Ensure that Kubernetes is deployed and all pods are running on the cluster.

    * It is advisable not to deploy Kserve immediately after deploying Kubernetes. Dell suggests allowing a 10-minute gap after Kubernetes installation for Kubernetes pods to stabilize.

    * MetalLB pod is up and running to provide an external IP to ``istio-ingressgateway``.

    * The domain name on the kubernetes cluster should be cluster.local. The Kserve inference service will not work with a custom ``cluster_name`` property on the kubernetes cluster.

    * Run ``local_repo.yml`` with ``kserve`` entry in ``software_config.json``.

    * Ensure the passed inventory file includes ``kube_control_plane`` and ``kube_node`` groups. `Click here <../../samplefiles.html>`_ for a sample file.

    * To access NVIDIA or AMD GPU accelerators for inferencing, Kubernetes NVIDIA or AMD GPU device plugin pods should be in running state. Kserve deployment does not deploy GPU device plugins.

**Deploy Kserve**

    1. Change directories to ``tools`` ::

        cd tools

    2. Run the ``kserve.yml`` playbook: ::

        ansible-playbook kserve.yml -i inventory

    Post deployment, the following dependencies are installed along with Kserve:

        * Istio (version: 1.20.4)
        * Certificate manager (version: 1.14.5)
        * Knative (version: 1.13.1)

    To verify the installation, run ``kubectl get pod -A`` and look for the namespaces: ``cert-manager``, ``istio-system``, ``knative-serving``, and ``kserve``. ::

                root@sparknode1:/tmp# kubectl get pod -A
                NAMESPACE              NAME                                                              READY   STATUS             RESTARTS        AGE
                cert-manager           cert-manager-5d999567d7-mfgdk                                     1/1     Running            0               44h
                cert-manager           cert-manager-cainjector-5d755dcf56-877dm                          1/1     Running            0               44h
                cert-manager           cert-manager-webhook-7f7b47c4d4-qzjst                             1/1     Running            0               44h
                default                model-store-pod                                                   1/1     Running            0               43h
                default                sklearn-pvc-predictor-00001-deployment-667d9f764c-clkbn           2/2     Running            0               43h
                istio-system           istio-ingressgateway-79cc8bf885-lqgm7                             1/1     Running            0               44h
                istio-system           istiod-777dc7ffbc-b4plt                                           1/1     Running            0               44h
                knative-serving        activator-59dff6d45c-28t2x                                        1/1     Running            0               44h
                knative-serving        autoscaler-dbf4d8d66-4wj8f                                        1/1     Running            0               44h
                knative-serving        controller-6bfd96676f-rdlxl                                       1/1     Running            0               44h
                knative-serving        net-istio-controller-6ff9b86f6b-9trb8                             1/1     Running            0               44h
                knative-serving        net-istio-webhook-845d4d74b4-r9d8z                                1/1     Running            0               44h
                knative-serving        webhook-678bd64859-q4ghb                                          1/1     Running            0               44h
                kserve                 kserve-controller-manager-f9c5984c5-xz7lp                         2/2     Running            0               44h

**Deploy inference service**

**Prerequisites**

    * To deploy a model joblib file with PVC as model storage, `click here <https://kserve.github.io/website/0.11/modelserving/storage/pvc/pvc/>`_
    * As part of Kserve deployment, Omnia deploys ``ClusterStorageContainer`` for supporting inference model download from the following endpoints:

            * prefix: gs://
            * prefix: s3://
            * prefix: hdfs://
            * prefix: webhdfs://
            * regex: https://(.+?).blob.core.windows.net/(.+)
            * regex: https://(.+?).file.core.windows.net/(.+)
            * regex: "https?://(.+)/(.+)"

    * Pull the intended inference model and the corresponding runtime-specific images into the nodes.
    * As part of the deployment, Omnia deploys `standard model runtimes. <https://github.com/kserve/kserve/releases/download/v0.11.2/kserve-runtimes.yaml>`_ To deploy a custom model, you might need to deploy required model runtime first.
    * To avoid problems with image to digest mapping when pulling inference runtime images, make the following config map changes:


        1. Edit ``knative-serving`` config map by executing the following command: ::

            kubectl edit configmap -n knative-serving config-deployment

        2. Add ``docker.io`` and ``index.docker.io`` as part of ``registries-skipping-tag-resolving``

            .. image:: ../../../images/kserve_config_map.png

    For more information, `click here. <../../../Troubleshooting/KnownIssues/Common/AITools.html>`_

**Access the inference service**

1. Deploy the inference service and verify that the service is up and running using the command: ``kubectl get isvc -A``. ::

    root@sparknode1:/tmp# kubectl get isvc -A
    NAMESPACE     NAME           URL                                      READY   PREV   LATEST   PREVROLLEDOUTREVISION   LATESTREADYREVISION           AGE
    default       sklearn-pvc    http://sklearn-pvc.default.example.com   True           100                              sklearn-pvc-predictor-00001   9m18s


2. Use ``kubectl get svc -A`` to check the external IP of the service ``istio-ingressgateway``. ::

    root@sparknode1:/tmp# kubectl get svc -n istio-system
    NAME                    TYPE           CLUSTER-IP      EXTERNAL-IP   PORT(S)                                      AGE
    istio-ingressgateway    LoadBalancer   10.233.30.227   10.20.0.101   15021:32743/TCP,80:30134/TCP,443:32241/TCP   44h
    istiod                  ClusterIP      10.233.18.185   <none>        15010/TCP,15012/TCP,443/TCP,15014/TCP        44h
    knative-local-gateway   ClusterIP      10.233.37.248   <none>        80/TCP                                       44h

3. To access inferencing from the ingressgateway with HOST header, run the below command from the ``kube_control_plane`` or ``kube_node``: ::

        curl -v -H "Host: <service url>" -H "Content-Type: application/json" "http://<istio-ingress external IP>:<istio-ingress port>/v1/models/<model name>:predict" -d @./iris-input.json

For example: ::

        root@sparknode2:/tmp# curl -v -H "Host: sklearn-pvc.default.example.com" -H "Content-Type: application/json" "http://10.20.0.101:80/v1/models/sklearn-pvc:predict" -d @./iris-input.json
        *   Trying 10.20.0.101:80...
        * Connected to 10.20.0.101 (10.20.0.101) port 80 (#0)
        > POST /v1/models/sklearn-pvc:predict HTTP/1.1
        > Host: sklearn-pvc.default.example.com
        > User-Agent: curl/7.81.0
        > Accept: */*
        > Content-Type: application/json
        > Content-Length: 76
        >
        * Mark bundle as not supporting multiuse
        < HTTP/1.1 200 OK
        < content-length: 21
        < content-type: application/json
        < date: Sat, 16 Mar 2024 09:36:31 GMT
        < server: istio-envoy
        < x-envoy-upstream-service-time: 7
        <
        * Connection #0 to host 10.20.0.101 left intact
        {"predictions":[1,1]}

.. note:: Refer to `image pull <../pullimagestonodes.html>`_ in case of ImagePullBackOff issue while deploying inference service.

**Remove Kserve**

    1. Delete all artifacts from the namespace, by entering the following commands:

        * ``kubectl delete all --all --namespace kserve``
        * ``kubectl delete all --all --namespace knative-serving``
        * ``kubectl delete all --all --namespace istio-system``
        * ``kubectl delete all --all --namespace cert-manager``

    2. Delete the namespace, by entering the following commands:

        * ``kubectl delete ns kserve``
        * ``kubectl delete ns knative-serving``
        * ``kubectl delete ns istio-system``
        * ``kubectl delete ns cert-manager``

.. warning:: Please be careful about any other required deployments sharing the above namespace. Deleting artifacts using ``--all`` will delete all artifacts in the namespace.