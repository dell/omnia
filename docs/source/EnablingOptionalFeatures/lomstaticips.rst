Setting Up Static IPs on LOM Devices
===================================

.. note:: All steps listed below are to be administered on the control plane. The DHCP provided IPs for these devices will be within the ``host_network_range`` irrespective of whether ``roce_network_nic`` is provided.

When the network interface type is set to shared LOM, users can manually assign static IPs to their networking (ethernet or Infiniband) or storage (powervault). Depending on whether the user set up a RoCe network and provided a ``roce_network_nic`` in ``base_vars.yml``, there are two ways users can achieve this:


**When ``roce_network_nic`` is provided:**

1. Get the pod name of the network-config pod: ``Kubectl get pods -n network-config``

2. Start a bash shell session with the pod: ``kubectl exec -it {{ pod_name }} -n network-config -- /bin/bash ``

3. Get the DHCP assigned IP of the device to be configured: ``cat /var/lib/dhcp/dhcpd.leases``

4. Go to AWX > Inventory > <device type> inventory >hosts and add the IP to the inventory.



**When ``roce_network_nic`` is not provided:**

1. Get the pod name of the cobbler pod: ``Kubectl get pods -n cobbler``

2. Start a bash shell session with the pod: ``kubectl exec -it {{ pod_name }} -n cobbler -- /bin/bash ``

3. Get the DHCP assigned IP of the device to be configured: ``cat /var/lib/dhcpd/dhcpd.leases``

4. Go to AWX > Inventory > <device type> inventory >hosts and add the IP to the inventory.
