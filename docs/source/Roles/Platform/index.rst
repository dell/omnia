AI platforms
-------------

If you want to install JupyterHub and Kubeflow playbooks, you have to first install the JupyterHub playbook and then install the Kubeflow playbook.

Commands to install JupyterHub and Kubeflow: ::

    ansible-playbook platforms/jupyterhub.yml -i inventory
    ansible-playbook platforms/kubeflow.yml -i inventory

.. note:: When the Internet connectivity is unstable or slow, it may take more time to pull the images to create the Kubeflow containers. If the time limit is exceeded, the **Apply Kubeflow configurations** task may fail. To resolve this issue, you must redeploy Kubernetes cluster and reinstall Kubeflow by completing the following steps:

* Format the OS on manager and compute nodes.

* In the ``omnia_config.yml`` file, change the ``k8s_cni`` variable value from calico to flannel.

* Run the Kubernetes and Kubeflow playbooks.

