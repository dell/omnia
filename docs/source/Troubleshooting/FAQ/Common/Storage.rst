Storage
=========

⦾ **Why does the** ``TASK [beegfs : Rebuilding BeeGFS client module]`` **fail?**

.. image:: ../../../images/BeeGFSFailure.png

**Potential Cause**: BeeGFS version 7.3.0 is in use.

**Resolution**: Use BeeGFS client version 7.3.1 while setting up BeeGFS on the cluster.