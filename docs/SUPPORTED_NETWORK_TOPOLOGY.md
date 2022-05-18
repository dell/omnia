# Network Topology
Possible network configurations include:

## Shared LOM
![img.png](images/SharedLomRoceNIC.png) <br>

<div class="tg-wrap"><table>
<thead>
  <tr>
    <th>Network Setup</th>
    <th>Roce_network_nic provided?</th>
    <th>Outcome</th>
    <th>One Touch Configuration Support</th>
  </tr>
</thead>
<tbody>
  <tr>
    <td rowspan="2">lom</td>
    <td>Yes</td>
    <td>When roce_network_nic is populated, management network container will come up, and it will be used to assign the management and data port IPs. This will provide internet connection if DNS settings are filled in base_vars.yml. Along with this , Cobbler PXE provisioning will be done over the high speed data path or roce.</td>
    <td>No</td>
  </tr>
  <tr>
    <td>No</td>
    <td>When roce_network_nic is not populated, cobbler container will come up and will be responsible for mgmt. and data IP assignment as well as for providing the DNS configurations( if the parameters are given)</td>
    <td>No</td>
  </tr>
</tbody>
</table></div>

>> __Note:__
>> * When `network interface` type is `lom`, `idrac_support` is assumed to be true irrespective of user input.
>> * Omnia will not automatically assign IPs to all devices (powervault or ethernet/Infiniband switches) when `network_interface_type` is lom. However, if required, users can follow the [linked steps](Installation_Guides/USING_AWX_PLAYBOOKS.md#setting-up-static-ips-on-devices-when-the-network-interface-type-is-shared-lom).
>> * Despite the value of `mgmt_network_nic` and `host_network_nic` being the same in LOM environments, the IPs assigned for management and data should not be in the same range. The start and end values of the management IP range and the host IP range cannot be the same.

## Dedicated NICs

![img.png](../docs/images/Dedicated_NIC_NetworkTopology.png) <br>
When the control plane has a separate NIC connected to ToR for Device Management to control various devices like iDRAC, switches and PowerVault, separate switches for management and host network are used. Omnia will run the management network POD for this network. An additional unmanaged switch is needed as a pass through switch.
<div class="tg-wrap"><table>
<thead>
  <tr>
   <th>network_interface_type</th>
   <th>device_config_support</th>
   <th>idrac_support</th>
   <th>Outcome</th>
   <th>One Touch Config Support</th>
  </tr>
</thead>
<tbody>
  <tr>
   <td rowspan="4">Dedicated</td>
   <td>TRUE</td>
   <td>TRUE</td>
   <td>Omnia  will assign IPs to all the management ports of the different devices. iDRAC  and PXE provisioning is supported. Here, ethernet, InfiniBand and powervault  configurations are supported.</td>
   <td>Yes</td>
  </tr>
  <tr>
   <td>TRUE</td>
   <td>FALSE</td>
   <td>An assert  failure on control_plane_common will manifest and Omnia Control Plane will  fail.</td>
   <td>No</td>
  </tr>
  <tr>
   <td>FALSE</td>
   <td>TRUE</td>
   <td>Assuming  the device_ip_list is populated, mgmt_container will not be used to assign  the IPs to all the mgmt ports as a device_ip_list indicates that IP  assignment is already done. However, ethernet, InfiniBand, powervault  configurations are supported.</td>
   <td>Yes</td>
  </tr>
  <tr>
   <td>FALSE</td>
   <td>FALSE</td>
   <td>No IPs  will be assigned by Omnia. Provisioning will only be through PXE.</td>
   <td>No</td>
  </tr>
</tbody>
</table></div>

>> __Note:__ If `device_config_support` is false (ie, no management container is set up), no IPs will be assigned by Omnia. If a device IP list is provided, provisioning will only be through PXE. 