General Query
==============

⦾ **Why does the** ``TASK [gather_facts_from_all_the_nodes]`` **get stuck while re-running** ``omnia.yml`` **playbook?**

**Potential Cause**: Corrupted entries in the ``/root/.ansible/cp/`` folder. For more information on this issue, `check this out <https://github.com/ansible/ansible/issues/17349>`_!

**Resolution**: Clear the directory ``/root/.ansible/cp/`` using the following commands: ::

    cd /root/.ansible/cp/

    rm -rf *

Alternatively, run the task manually: ::

    cd omnia/utils/cluster
    ansible-playbook gather_facts_resolution.yml


⦾ **What to do if** ``omnia.yml`` **execution fails with a** ``403: Forbidden`` **error when an NFS share is provided as the** ``repo_store_path`` **?**

.. image:: ../../../images/omnia_NFS_403.png

**Potential Cause**: For ``omnia.yml`` execution, the NFS share folder provided in ``repo_store_path`` must have 755 permissions.

**Resolution**: Ensure that the NFS share folder provided as the ``repo_store_path`` has 755 permissions, and re-run ``omnia.yml``.