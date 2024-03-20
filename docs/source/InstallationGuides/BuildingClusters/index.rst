Configuring the cluster
=======================

**Features enabled by omnia.yml**

    * Centralized authentication: Once all the required parameters in `security_config.yml <schedulerinputparams.html>`_ are filled in, ``omnia.yml`` can be used to set up FreeIPA/LDAP.

    * Slurm: Once all the required parameters in `omnia_config.yml <schedulerinputparams.html>`_ are filled in, ``omnia.yml`` can be used to set up slurm.

    * Login Node (Additionally secure login node)

    * Kubernetes: Once all the required parameters in `omnia_config.yml <schedulerinputparams.html>`_ are filled in, ``omnia.yml`` can be used to set up kubernetes.

.. toctree::
    schedulerinputparams
    schedulerprereqs
    installscheduler
    Authentication
    KubernetesAccess
    BeeGFS
    NFS




