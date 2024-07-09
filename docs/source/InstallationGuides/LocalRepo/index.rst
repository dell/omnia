Local repositories for the  cluster
=====================================

The local repository feature will help create offline repositories on the control plane which all the cluster nodes will access. ``local_repo/local_repo.yml`` runs with inputs from ``input/software_config.json`` and ``input/local_repo_config.yml``:

.. caution:: Minimal OS version of RHEL and Rocky Linux and "desktop image" version of Ubuntu is not supported on the control plane.

.. toctree::
    Prerequisite
    InputParameters
    localrepos
    RunningLocalRepo
    CustomLocalRepo



