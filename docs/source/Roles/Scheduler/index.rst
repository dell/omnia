Scheduler
==========

The scheduler role sets up `Kubernetes <https://kubernetes.io/>`_ and `Slurm <https://slurm.schedmd.com/documentation.html>`_.

**Slurm job based user access**

To ensure security while running jobs on the cluster, users can be assigned permissions to access compute nodes only while their jobs are running. To enable the feature: ::

    cd omnia
    ansible-playbook job_based_user_access.yml -i inventory

.. note::


    The inventory queried in the above command is to be created by the user prior to running ``omnia.yml``.

    Slurm and IPA client need to installed on the nodes before running this playbook.

    Only users added to the 'slurm' group can execute slurm jobs. To add users to the group, use the command: ``usermod -a -G slurm <username>``.