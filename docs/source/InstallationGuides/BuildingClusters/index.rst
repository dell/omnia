Configuring the cluster
=======================

**Features enabled by omnia.yml**

    * Centralized authentication: Once all the required parameters in `security_config.yml <schedulerinputparams.html>`_ are filled in, ``omnia.yml`` can be used to set up FreeIPA/LDAP.

    * Slurm: Once all the required parameters in `omnia_config.yml <schedulerinputparams.html>`_ are filled in, ``omnia.yml`` can be used to set up slurm.

    * Login Node (Additionally secure login node)

    * Kubernetes: Once all the required parameters in `omnia_config.yml <schedulerinputparams.html>`_ are filled in, ``omnia.yml`` can be used to set up kubernetes.

    * BeeGFS bolt on installation: Once all the required parameters in `storage_config.yml <schedulerinputparams.html>`_ are filled in, ``omnia.yml`` can be used to set up NFS.

    * NFS bolt on support: Once all the required parameters in `storage_config.yml <schedulerinputparams.html>`_ are filled in, ``omnia.yml`` can be used to set up BeeGFS.

    * Telemetry: Once all the required parameters in `telemetry_config.yml <schedulerinputparams.html>`_ are filled in, ``omnia.yml`` sets up `Omnia telemetry and/or iDRAC telemetry <../../Roles/Telemetry/index.html>`_. It also installs `Grafana <https://grafana.com/>`_ and `Loki <https://grafana.com/oss/loki/>`_ as Kubernetes pods.

.. toctree::
    schedulerinputparams
    schedulerprereqs
    installscheduler
    Authentication
    BeeGFS
    NFS
    OneAPI
    OpenMPI_AOCC
    KernelUpdateRHEL



