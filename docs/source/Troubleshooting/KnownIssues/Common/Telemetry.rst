Telemetry
==========

⦾ **Why does the** ``TASK [loki : Start Docker Service`` **fail with** ``Job for docker.service failed because the control process exited with error code`` **while executing** ``upgrade.yml`` **playbook?**

.. image:: ../../../images/loki_docker.png

**Potential Cause**: This issue may arise when the ‘docker0’ interface is already bound to a zone in the firewall settings and Docker tries to use this interface, resulting in a ‘Zone Conflict’.

**Resolution**: Perform the following steps to adjust your firewall settings, allowing Docker to utilize the 'docker0' interface without encountering conflicts.

1. Add the the docker0 interface to the docker zone using the following command: ::

       sudo firewall-cmd --zone=docker --add-interface=docker0 --permanent

2. Reload the firewall to apply the changes, using the following command: ::

        sudo firewall-cmd --reload

3. Restart docker service to ensure it picks up the changes, using the following command: ::

        sudo systemctl restart docker

4. Finally, run the following command to ensure docker service is active and running: ::

        systemctl status docker

After performing all the above steps, re-run ``upgrade.yml`` playbook.