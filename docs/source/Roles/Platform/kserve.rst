Setup Kserve
--------------

Kserve is an open-source serving platform that simplifies the deployment, scaling, and management of machine learning models in production environments, ensuring efficient and reliable inference capabilities. For more information, `click here. <https://kserve.github.io/website/0.11/get_started/>`_ Omnia deploys KServe (v0.11.0) on the kubernetes cluster. Once KServe is deployed, any inference service can be installed on the kubernetes cluster.


**Prerequisites**

    * Ensure nerdctl and containerd is available on all cluster nodes.

    * The cluster is deployed with Kubernetes.

    * MetalLB pod is up and running to provide an external IP to ``istio-ingressgateway``.

    * The domain name on the kubernetes cluster should be **cluster.local**. The KServe inference service will not work with a custom ``cluster_name`` property on the kubernetes cluster.

    * A local Kserve repository should be created using ``local_repo.yml``. For more information, `click here. <../../InstallationGuides/LocalRepo/kserve.html>`_

    * Ensure the passed inventory file includes a ``kube_control_plane`` and a ``kube_node`` listing all cluster nodes. `Click here <../../samplefiles.html>`_ for a sample file.

    * To access NVIDIA or AMD GPU acceleration in inferencing, Kubernetes NVIDIA or AMD GPU device plugins need to be installed during Kubernetes deployment. ``kserve.yml`` does not deploy GPU device plugins.

**Deploy KServe**

    1. Change directories to ``tools``. ::

        cd tools

    2. Run the ``kserve.yml`` playbook: ::

        ansible-playbook kserve.yml -i inventory

    Post deployment, the following dependencies are installed:

        * Istio (version: 1.17.0)
        * Certificate manager (version: 1.13.0)
        * Knative (version: 1.11.0)

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
    * Verify that the inference service is up and running using the command: ``kubectl get isvc -A``.::

            root@sparknode1:/tmp# kubectl get isvc -A
            NAMESPACE     NAME           URL                                      READY   PREV   LATEST   PREVROLLEDOUTREVISION   LATESTREADYREVISION           AGE
            default       sklearn-pvc    http://sklearn-pvc.default.example.com   True           100                              sklearn-pvc-predictor-00001   9m18s


    * Pull the intended inference model and the corresponding runtime-specific images into the nodes.
    * As part of the deployment, Omnia deploys `standard model runtimes. <https://github.com/kserve/kserve/releases/download/v0.11.0/kserve-runtimes.yaml>`_ If a custom model is deployed, deploy a custom runtime first.
    * To avoid problems with image to digest mapping when pulling inference runtime images, `click here. <../../Troubleshooting/KnownIssues.html>`_


**Access the inference service**

1. Use ``kubectl get svc -A`` to check the external IP of the service ``istio-ingressgateway``. ::

    root@sparknode1:/tmp# kubectl get svc -n istio-system
    NAME                    TYPE           CLUSTER-IP      EXTERNAL-IP   PORT(S)                                      AGE
    istio-ingressgateway    LoadBalancer   10.233.30.227   10.20.0.101   15021:32743/TCP,80:30134/TCP,443:32241/TCP   44h
    istiod                  ClusterIP      10.233.18.185   <none>        15010/TCP,15012/TCP,443/TCP,15014/TCP        44h
    knative-local-gateway   ClusterIP      10.233.37.248   <none>        80/TCP                                       44h

2. To access inferencing from the ingressgateway with HOST header, run the below command from the kube_control_plane or kube_node: ::

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






