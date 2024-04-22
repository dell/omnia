Setup Kubeflow
---------------
Kubeflow is an open-source platform for machine learning and MLOps on Kubernetes introduced by Google.

**Prerequisite**

Ensure that you have executed ``local_repo.yml`` with Kubeflow specified in the ``software_config.json`` file.an

**Deploy Kubernetes**

First, ensure that you have a Kubernetes cluster deployed on your compute node.

    Instructions to set up Kubernetes:

        * Run the ``omnia.yml`` or ``scheduler.yml`` playbook to deploy Kubernetes.
        * Ensure dynamic NFS provisioning is enabled through the ``storage.yml`` playbook.

.. note:: The playbooks automate the process, ensuring consistency across deployments.

**Deploy Kubeflow**

Commands to install Kubeflow: ::

    ansible-playbook tools/kubeflow.yml -i inventory

**Obtain External IP of Ingress Gateway**

Once Kubeflow is deployed, you need to obtain the external IP address of the ingress gateway. Check the external IP address of the ingress gateway using command-line tools like ``kubectl``. This IP address will be used to access the Kubeflow dashboard.

**Accessing the Kubeflow Dashboard**

After obtaining the external IP address of the ingress gateway, you can access the Kubeflow dashboard using a web browser.

    Instructions to access Kubeflow dashboard:

        * Open any browser of your choice and go to `<http://external_ip:80>`_.
        * You will be redirected to the Dex login page. You can find a sample image below.

        .. image:: ../../images/dex_login.png

**Logging into the Kubeflow dashboard**

To log in to the Kubeflow dashboard and start using its features, you need to provide the default username and password.

        * **Username**: user@example.com
        * **Password**: 12341234

For more details, refer to Kubeflow manifest documentation link `here. <https://github.com/kubeflow/manifests?tab=readme-ov-file#overview>`_