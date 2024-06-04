Configuring the cluster
=======================

**Features enabled by omnia.yml**

    * Centralized authentication: Once all the required parameters in `security_config.yml <schedulerinputparams.html>`_ are filled in, ``omnia.yml`` can be used to set up FreeIPA/LDAP.

    * Slurm: Once all the required parameters in `omnia_config.yml <schedulerinputparams.html>`_ are filled in, ``omnia.yml`` can be used to set up slurm.

    * Kubernetes: Once all the required parameters in `omnia_config.yml <schedulerinputparams.html>`_ are filled in, ``omnia.yml`` can be used to set up kubernetes.

    * Login Node (Additionally secure login node)


.. toctree::
    schedulerinputparams
    schedulerprereqs
    installscheduler
    install_kubernetes
    k8s_plugin_roce_nic
    install_slurm
    install_ucx_openmpi
    Authentication
    KubernetesAccess
    BeeGFS
    NFS




