Step 5: Configure the cluster
================================

**Features enabled by omnia.yml**:

    * **Centralized authentication**: Once all the required parameters in `security_config.yml <schedulerinputparams.html#security-config-yml>`_ are filled in, ``omnia.yml`` can be used to set up FreeIPA/OpenLDAP.

    * **Slurm**: Once all the required parameters in `omnia_config.yml <schedulerinputparams.html#id13>`_ are filled in, ``omnia.yml`` can be used to set up slurm.

    * **Kubernetes**: Once all the required parameters in `omnia_config.yml <schedulerinputparams.html#id12>`_ are filled in, ``omnia.yml`` can be used to set up kubernetes.

    * **Login Node (Additionally secure login node)**

.. caution:: If you have a proxy server set up for your OIM, you must configure the proxy environment variables on the OIM before running any Omnia playbooks. For more information, `click here <../Setup_CP_proxy.html>`_.

.. toctree::
    :maxdepth: 2

    schedulerprereqs
    schedulerinputparams
    BuildingCluster/index






