Setup Kubeflow
---------------
Kubeflow is an open-source platform for machine learning and MLOps on Kubernetes introduced by Google.

Commands to install Kubeflow: ::

    ansible-playbook tools/kubeflow.yml -i inventory

.. note:: When the Internet connectivity is unstable or slow, it may take more time to pull the images to create the Kubeflow containers. If the time limit is exceeded, the **Apply Kubeflow configurations** task may fail.


