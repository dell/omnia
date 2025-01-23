Step 2: Create Local repositories for the cluster
==================================================

The ``local_repo.yml`` playbook creates offline repositories on the OIM server, which all the cluster nodes will access. This playbook execution requires inputs from ``input/software_config.json`` and ``input/local_repo_config.yml``.

.. caution:: If you have a proxy server set up for your OIM, you must configure the proxy environment variables on the OIM before running any Omnia playbooks. For more information, `click here <../Setup_CP_proxy.html>`_.

.. toctree::
    Prerequisite
    InputParameters
    localrepos
    RunningLocalRepo

