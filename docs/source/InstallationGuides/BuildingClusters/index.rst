Configuring the cluster
=======================

**Features enabled by omnia.yml**

    * Centralized authentication: Once all the required parameters in `security_config.yml <schedulerinputparams.html>`_ are filled in, ``omnia.yml`` can be used to set up FreeIPA/LDAP.

    * Slurm: Once all the required parameters in `omnia_config.yml <schedulerinputparams.html>`_ are filled in, ``omnia.yml`` can be used to set up slurm.

    * Login Node (Additionally secure login node)

    * Kubernetes: Once all the required parameters in `omnia_config.yml <schedulerinputparams.html>`_ are filled in, ``omnia.yml`` can be used to set up kubernetes.

    * BeeGFS bolt on installation: Once all the required parameters in `storage_config.yml <schedulerinputparams.html>`_ are filled in, ``omnia.yml`` can be used to set up NFS.

    * NFS bolt on support: Once all the required parameters in `storage_config.yml <schedulerinputparams.html>`_ are filled in, ``omnia.yml`` can be used to set up BeeGFS.

    * Telemetry: To visualize the cluster (Slurm/Kubernetes) metrics on Grafana (On the control plane)  during the run of ``omnia.yml``, add the parameters ``grafana_username`` and ``grafana_password`` (That is ``ansible-playbook omnia.yml -i inventory -e grafana_username="" -e grafana_password=""``). Alternatively, Grafana is not installed by ``omnia.yml`` if it's not available on the Control Plane.

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



