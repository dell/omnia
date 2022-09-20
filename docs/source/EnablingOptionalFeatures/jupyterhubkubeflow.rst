Install JupyterHub and Kubeflow Playbooks
=============================================


If you want to install **JupyterHub** and **Kubeflow** playbooks, you have to first install the **JupyterHub** playbook and then install the **Kubeflow** playbook.

To install **JupyterHub** and **Kubeflow** playbooks:

1. From AWX UI, under **RESOURCES** -> **Templates**, select **DeployOmnia** template.

2. From **PLAYBOOK** dropdown menu, select **platforms/jupyterhub.yml** and launch the template to install JupyterHub playbook.

3. From **PLAYBOOK** dropdown menu, select **platforms/kubeflow.yml** and launch the template to install Kubeflow playbook.



The same playbooks can also be installed via CLI using:

1. ``ansible-playbook platforms/jupyterhub.yml -i inventory``

2. ``ansible-playbook platforms/kubeflow.yml -i inventory``



.. note::When the Internet connectivity is unstable or slow, it may take more time to pull the images to create the Kubeflow containers. If the time limit is exceeded, the **Apply Kubeflow configurations** task may fail. To resolve this issue, you must redeploy Kubernetes cluster and reinstall Kubeflow by completing the following steps:

         1. Complete the PXE booting of the head and compute nodes.

         2. In the ``omnia_config.yml`` file, change the k8s_cni variable value from calico to flannel.

         3. Run the Kubernetes and Kubeflow playbooks.



 If you want to view or edit the ``omnia_config.yml`` file, run the following commands:

         - ``ansible-vault view omnia_config.yml --vault-password-file .omnia_vault_key`` -- To view the file.

         - ``ansible-vault edit omnia_config.yml --vault-password-file .omnia_vault_key`` -- To edit the file.
