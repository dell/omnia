Setup Kserve
--------------

Kserve is an open-source serving platform that simplifies the deployment, scaling, and management of machine learning models in production environments, ensuring efficient and reliable inference capabilities. For more information, `click here. <https://kserve.github.io/website/0.11/get_started/>`_ Omnia deploys KServe (v0.11.0) on the kubernetes cluster. Once KServe is deployed, any inference service can be installed on the kubernetes cluster.


**Prerequisites**

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

    To verify the installation, run ``kubectl get pod -A`` and look for the namespaces: ``cert-manager``, ``istio-system``, ``knative-serving``, and ``kserve``.

**Deploy inference service**

**Prerequisites**

    * Verify that the inference service is up and running using the command: ``kubectl get isvc -A``.
    * Pull the intended inference model and the corresponding runtime-specific images into the nodes.
    * As part of the deployment, Omnia deploys `standard model runtimes. <https://github.com/kserve/kserve/releases/download/v0.11.0/kserve-runtimes.yaml>`_ If a custom model is deployed, deploy a custom runtime first.

**Access the inference service**

1. Use ``kubectl get svc -A`` to check the external IP of the service ``istio-ingressgateway``.
2. To access inferencing from the ingressgateway with HOST header, run the below command: ::

        curl -v -H "Host: <service url>" -H "Content-Type: application/json" "http://<istio-ingress external IP>:<istio-ingress port>/v1/models/<model name>:predict" -d @./iris-input.json

For example: ::

    curl -v -H "Host: sklearn-pvc.default.example.com" -H "Content-Type: application/json" "http://10.20.0.101:80/v1/models/sklearn-pvc:predict" -d @./iris-input.json






