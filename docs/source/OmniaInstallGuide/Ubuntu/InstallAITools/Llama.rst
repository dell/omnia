Deploying Dell Enterprise Pretrained model on the cluster
===========================================================

This guide provides a step-by-step approach to deploy the pretrained model from `Dell Enterprise Hub <https://dell.huggingface.co/>`_. The Meta-Llama-3.1-8b-Instruct model will be deployed as a sample model on a ``kube_control_plane`` node, specifically optimized for **NVIDIA** platforms. The model is containerized and validated to run seamlessly on the latest Dell hardware. By following this documentation, users can deploy the model, run inferences, or delete the service using a standalone Python script.

The python script is located in the ``omnia/example/ai_examples/nvidia/dell_pretrained_model`` directory. The python script file is named ``dell_pretrained_model_nvidia.py``.

Prerequisites
--------------

Before deployment, the following prerequisites must be fulfilled:


1. This sample Meta-Llama-3.1-8b-Instruct pretrained model needs atleast one NVIDIA GPU. This means that the cluster should have atleast one node with an NVIDIA GPU to deploy this model. If you switch to a different model, the GPU requirement might vary.

2. Kubernetes must be installed and configured on the cluster.

3. The cluster must have access to the public internet in order to download the model image. If your cluster has a proxy server set up, refer to the page `here <../pullimagestonodes.html>`_ for enabling internet via that proxy.

4. Python 3.x must be installed on the cluster. The script relies on several Python modules, including:

   * **Standard Library Modules**: Already included with Python 3.x (subprocess, time, argparse, logging, sys, ipaddress).
   * **Third-Party Modules**: The requests module must be installed manually if not available by default. You can install it using the following command: ::

       pip install requests

.. note:: If you're executing the script within the Omnia virtual environment, the requests module is already installed and available on the cluster. In case you run the script outside of the Omnia virtual environment, you might need to install the module manually.

5. The ``dell_pretrained_model_nvidia.py`` file present in the ``omnia/example/ai_examples/nvidia/dell_pretrained_model`` must be copied to the ``kube_control_plane`` from the control plane server.


Usage Instructions
--------------------

Follow the below steps to use the Python script in order to deploy, infer, or delete the model service on your Kubernetes cluster:

1. **Deploy the model and service**

    To deploy the model and create the associated service, run: ::

        python3 dell_pretrained_model_nvidia.py --deploy

2. **Execute an inference job**

    * To execute an inference job from the ``kube_control_plane`` using the default query, run: ::

        python3 dell_pretrained_model_nvidia.py --infer

    * To execute an inference job from the ``kube_control_plane`` using a specific query, run: ::

        python3 dell_pretrained_model_nvidia.py --infer "<Your_query_here>"

    * To execute an inference job from outside of the ``kube_control_plane`` using a specific service IP and default query, run: ::

        python3 dell_pretrained_model_nvidia.py --infer --service-ip <pretrained-model-service-ip>

    * To execute an inference job from outside of the ``kube_control_plane`` using a specific service IP and a specific query, run: ::

        python3 dell_pretrained_model_nvidia.py --infer "<Your_query_here>" --service-ip <pretrained-model-service-ip>

    .. note:: If you're not aware of the ``service_IP`` of the pretrained model service, use the following command: ::

        kubectl get svc pretrained-model-service

       *Where the service IP address will be listed under the EXTERNAL-IP column.*

3. **Delete the deployed model and service**

    To delete the deployed model and service, run: ::

        python3 dell_pretrained_model_nvidia.py --delete

Additional Instructions
-------------------------

*  **Model selection**: To select and download a model from the Dell registry, visit `Dell's Hugging Face Hub <https://dell.huggingface.co/>`_. Log in using your Hugging Face Hub account credentials to access the models.
*  **Deploying other models**: You can deploy other models from the Dell registry for NVIDIA platforms by modifying the ``PRETRAINED_MODEL_CONFIG`` section of the ``dell_pretrained_model_nvidia.py`` file with the desired model image. Ensure the new service name does not conflict with any existing service names, and verify that all other configurations and resource requirements are correct as per the model specifications.
*  **Hugging Face token**: If the model requires a Hugging Face token, replace the ``user_HF_token`` value in ``PRETRAINED_MODEL_CONFIG`` section of the ``dell_pretrained_model_nvidia.py`` file with the correct token.
*  **Resource availability**: Ensure that sufficient computational resources (GPU, memory) are available on the Kubernetes nodes to deploy and run the models effectively. This includes verifying that the nodes meet the model's requirements for optimal performance.


