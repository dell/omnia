Deploying Llama 3.1-8B on the cluster
=======================================

This guide provides a step-by-step approach to deploy the Meta-Llama-3.1-8b-Instruct model on a kubernetes cluster, specifically optimized for NVIDIA platforms. The model, sourced from the `Dell Enterprise Hub <https://dell.huggingface.co/>`_, is fully containerized and validated to run seamlessly on the latest Dell hardware. By following this documentation, users can deploy the model, run inferences, or delete the service using a Python script.

Prerequisites
--------------

Before deployment, the following prerequisites must be fulfilled:

1. Kubernetes must be installed and configured on the cluster.

2. The cluster must have access to the public internet in order to download the model image. If your cluster has a proxy server set up, refer to the page `here <../pullimagestonodes.html>`_ for enabling internet via that proxy.

3. Python 3.x must be installed on the cluster. The script relies on several Python modules, including:

    * Standard Library Modules: Already included with Python 3.x (subprocess, time, argparse, logging, sys, ipaddress).
    * Third-Party Modules: The requests module must be installed manually if not available by default. You can install it using the following command: ::

        pip install requests

.. note:: If you're executing the script within the Omnia virtual environment, the requests module is already installed and available on the cluster. In case you run the script outside of the Omnia virtual environment, you might need to install the module manually.

Usage Instructions
--------------------

Follow the below steps to use the Python script in order to deploy, infer, or delete the model service on your Kubernetes cluster:

1. **Deploy the model and service**

    To deploy the model and create the associated service, run: ::

        python dell_pretrained_model_nvidia.py --deploy

2. **Execute an inference job**

    * To execute an inference job from the ``kube_control_plane`` using the default query, run: ::

        python dell_pretrained_model_nvidia.py --infer

    * To execute an inference job from the ``kube_control_plane`` using a specific query, run: ::

        python dell_pretrained_model_nvidia.py --infer "<Your_query_here>"

    * To execute an inference job from outside of the ``kube_control_plane`` using a specific service IP and default query, run: ::

        python dell_pretrained_model_nvidia.py --infer --service-ip <service_IP>

    * To execute an inference job from outside of the ``kube_control_plane`` using a specific service IP and a specific query, run: ::

        python dell_pretrained_model_nvidia.py --infer "<Your_query_here>" --service-ip <service_IP>

    .. note:: If you're not aware of the ``service_IP`` of the pretrained model service, use the following command: ::

        kubectl get svc

       Where the service IP address will be listed under the ``EXTERNAL-IP`` column.

3. **Delete the deployed model and service**

    To delete the deployed model and service, run: ::

        python dell_pretrained_model_nvidia.py --delete

Additional Instructions
-------------------------

*  **Model selection**: To select and download a model from the Dell registry, visit `Dell's Hugging Face Hub <https://dell.huggingface.co/>`_. Log in using your Hugging Face Hub account credentials to access the models.
*  **Deploying other models**: You can deploy other models from the Dell registry for NVIDIA platforms by modifying the ``PRETRAINED_MODEL_CONFIG`` file with the desired model image. Ensure the new service name does not conflict with any existing service names, and verify that all other configurations and resource requirements are correct as per the model specifications.
*  **Hugging Face token**: If the model requires a Hugging Face token, replace the ``user_HF_token`` value in ``PRETRAINED_MODEL_CONFIG`` file with the correct token.
*  **Resource availability**: Ensure that sufficient computational resources (GPU, memory) are available on the Kubernetes nodes to deploy and run the models effectively. This includes verifying that the nodes meet the model's requirements for optimal performance.


