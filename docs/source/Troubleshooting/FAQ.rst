Frequently Asked Questions
==========================

**Why does splitting an ethernet Z series port fail with "Failed. Either port already split with different breakout value or port is not available on ethernet switch"?**


Potential Cause:

    1. The port is already split.

    2. It is an even-numbered port.

Resolution:

    Changing the ``breakout_value`` on a split port is currently not supported. Ensure the port is un-split before assigning a new ``breakout_value``.


**How to enable DHCP routing on Compute Nodes:**

To enable routing, update the ``primary_dns`` and ``secondary_dns`` in ``provision_config.yml`` with the appropriate IPs (hostnames are currently not supported). For compute nodes that are not directly connected to the internet (ie only host network is configured), this configuration allows for internet connectivity.


**What to do if the LC is not ready:**


* Verify that the LC is in a ready state for all servers: ``racadm getremoteservicesstatus``

* PXE boot the target server.

**Is Disabling 2FA supported by Omnia?**

* Disabling 2FA is not supported by Omnia and must be manually disabled.

**Is provisioning servers using BOSS controller supported by Omnia?**

Provisioning server using BOSS controller is now supported by Omnia 1.2.1.


**How to re-launch services after a control-plane reboot while running provision.yml**

After a reboot of the control plane while running ``provision.yml``, to bring up ``xcatd`` services, please run the below commands: ::

    systemctl restart postgresql.service

    systemctl restart xcatd.service

**How to re-provision a server once it's been set up by xCAT**

* Use ``lsdef -t osimage | grep install-compute`` to get a list of all valid OS profiles.

* Use ``nodeset all osimage=<selected OS image from previous command>`` to provision the OS on the target server.

* PXE boot the target server to bring up the OS.