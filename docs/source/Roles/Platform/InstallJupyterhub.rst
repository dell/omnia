Using Jupyterhub
-----------------

Using Helm charts, Omnia can install Jupyterhub on Kubernetes clusters. Once Jupyterhub is deployed, log into the UI to create your own notebook servers. For more information, `click here <https://z2jh.jupyter.org/en/stable/jupyterhub/customization.html>`_.

**Prerequisites**

* Ensure the kubernetes cluster is setup and working. If NVidia or AMD GPU acceleration is required for the notebook, install the Kubernetes NVidia or AMD GPU device plugin during Kubernetes deployment.
* Ensure the inventory file includes a ``kube_control_plane`` group listing all cluster nodes.
* Review the ``omnia/tools/roles/jupyter_config.yml`` file to ensure that the deployment meets your requirements. If not, modify the file.
* Update the ``omnia/input/software_config.json`` file with the correct jupyter helm chart version required. The default value is **3.2.0**.
* Omnia deploys the ``quay.io/jupyterhub/k8s-singleuser-sample:3.2.0`` image irrespective of whether the intended notebooks are CPU-only, NVidia GPU, or AMD GPU.  To use a custom image, modify the ``omnia/tools/roles/jupyter_config.yml`` file.


**Deploying Jupyterhub**

1. Change directories to the ``tools`` folder: ::

    cd tools

2. Run the ``jupyterhub.yml`` playbook using: ::

       ansible-playbook jupyterhub.yml -i inventory

.. note:: The default namespace for deployment is ``jupyterhub-omnia-ns``.


**Accessing the Jupyterhub UI**

1. Verify that the Jupyterhub service is running using metallb loadbalancer.
2. Find the IP address of the Jupyterhub service using: ::

        kubectl get svc -n jupyterhub-omnia-ns

The IP address is listed against ``proxy-public-service``.

3. For the first log in, use the Login Node. Ensure the login node has an OS installed with GUI support. Use any browser to log in with user credentials.
4. Choose your preferred notebook server option and click on **Start**. A pod will be created for the user. Available server options will depend on the user logging in.

**Stopping the Notebook server**

1. Click **File > Hub Control Plane**.
2. Select **Stop Server**.

**Note:** Stopping the notebook server only terminates the user pod. The users data persists and can be accessed by loggin in and starting the notebook server again.
