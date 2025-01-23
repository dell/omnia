Step 6: Install AI tools
===============================

AI (Artificial Intelligence) tools are software applications or systems that use AI technologies such as machine learning, natural language processing (NLP), computer vision, and deep learning to perform various tasks autonomously or with human interaction. These tools are designed to mimic human intelligence and can be used across different industries and domains for purposes such as automation, data analysis, decision-making, and more.

.. caution::
    Omnia targets all nodes that appear in the Kubernetes inventory when deploying the desired AI toolset; that is, the AI tool will be deployed on every Kubernetes node mentioned in the inventory. Ensure to mention all the desired nodes in the Kubernetes inventory file while deploying the AI tools via their respective playbooks. For more information on how to set up Kubernetes, `click here <../OmniaCluster/BuildingCluster/install_kubernetes.html>`_.

.. toctree::

    InstallJupyterhub
    kubeflow
    vLLM/index
    Pytorch
    TensorFlow
    kserve