Slurm job based user access
===========================

To ensure security while running jobs on the cluster, users can be assigned permissions to access compute nodes only while their jobs are running. To enable the feature: ::

    cd scheduler
    ansible-playbook job_based_user_access.yml -i inventory


.. note::

    * The inventory queried in the above command is to be created by the user prior to running ``omnia.yml`` as ``scheduler.yml`` is invoked by ``omnia.yml``

    * Only users added to the 'slurm' group can execute slurm jobs. To add users to the group, use the command: ``usermod -a -G slurm <username>``.
