# Custom ISO provisioning on Dell EMC PowerEdge Servers

* Enter the information required in `input_params/base_vars.yml`, `input_params/login_vars.yml` and `idrac_vars.yml` per the provided [Input Parameter Guides](../Input_Parameter_Guide).

## Configuring Servers with Out-of-Band Management (Provision Method: iDRAC)

### Generating a Custom ISO
* Using the Omnia role _control_plane_customiso_, a custom ISO is generated. Based on the parameters entered above, the Kickstart file is configured and added to the custom ISO file. The *unattended_centos7.iso*, *unattended_rocky8.iso* or *unattended_leap15.iso* file is copied to an NFS share on the control plane to provision the PowerEdge servers using iDRAC. 

### Run idrac_template on the AWX UI.
1. Run `kubectl get svc -n awx`.
2. Copy the Cluster-IP address of the awx-ui. 
3. To retrieve the AWX UI password, run `kubectl get secret awx-admin-password -n awx -o jsonpath="{.data.password}" | base64 --decode`.
4. Open the default web browser on the control plane and enter `http://<IP>:8052`, where IP is the awx-ui IP address and 8052 is the awx-ui port number. Log in to the AWX UI using the username as `admin` and the retrieved password.  
5. Under __RESOURCES__ -> __Templates__, launch the **idrac_template**.

Omnia role used to provision custom ISO on PowerEdge Servers using iDRAC: *provision_idrac*  

For the `idrac.yml` file to successfully provision the custom ISO on the PowerEdge Servers, ensure that the following prerequisites are met:
* The **idrac_inventory** file is updated with the iDRAC IP addresses.
* Required input parameters are updated in the **idrac_vars.yml** file under **omnia/control_plane/input_params** directory.
* An *unattended_centos7.iso*, *unattended_rocky8.iso* or *unattended_leap15.iso* file is available in an NFS path.
* The Lifecycle Controller Remote Services of PowerEdge Servers is in the 'ready' state.
* The Redfish services are enabled in the iDRAC settings under **Services**.
* The PowerEdge Servers have the iDRAC Enterprise or Datacenter license. If the license is not found, servers will be PXE booted and provisioned using Cobbler.  
* If `provision_method` is set to PXE in `base_vars.yml`, ensure that all PXE devices have a configured, active NIC. To verify/ configure NIC availability: On the server, go to `BIOS Setup -> Network Settings -> PXE Device`. For each listed device (typically 4), configure/ check for an active NIC under `PXE device settings`
* iDRAC 9 based Dell EMC PowerEdge Servers with firmware versions 5.00.10.20 and above. (With the latest BIOS available)

The **provision_idrac** file configures and validates the following:
* Required input parameters and prerequisites.
* BIOS and SNMP settings.
* The latest available version of the iDRAC firmware is updated.
* If bare metal servers have a RAID controller installed, Virtual disks are created for RAID configuration.
* Availability of iDRAC Enterprise or Datacenter License on iDRAC.  

After the configurations are validated, the **provision_idrac** file provisions the custom ISO on the PowerEdge Servers. After the OS is provisioned successfully, iDRAC IP addresses are updated in the *provisioned_idrac_inventory* in AWX.

>>**Note**:
>> * The `idrac.yml` file initiates the provisioning of custom ISO on the PowerEdge servers. Wait for some time for the node inventory to be updated on the AWX UI. 
>> * Due to the latest `catalog.xml` file, Firmware updates may fail for certain components. Omnia execution doesn't get interrupted but an error gets logged on AWX. For now, please download those individual updates manually.
>> * If a server is connected to an Infiniband Switch via an Infiniband NIC, Omnia will not activate this NIC. Use the below instructions depending on the OS.
>> * For servers running Rocky,Infiniband NICs can be manually enabled using `ifup <InfiniBand NIC>`.
>> * If your server is running LeapOS, ensure the following pre-requisites are met before manually bringing up the interface:
>> 	1. The following repositories have to be installed:
>> 		* [Leap OSS](http://download.opensuse.org/distribution/leap/15.3/repo/oss/)
>> 		* [Leap Non OSS](http://download.opensuse.org/distribution/leap/15.3/repo/non-oss/)
>> 	2. Run: `zypper install -n rdma-core librdmacm1 libibmad5 libibumad3 infiniband-diags` to install IB NIC drivers.  (If the drivers do not install smoothly, reboot the server to apply the required changes)
>> 	3. Run: `service network status` to verify that `wicked.service` is running.
>> 	4. Verify that the ifcfg-<InfiniBand NIC> file is present in `/etc/sysconfig/network`
>> 	5. Once all the pre-requisites are met, bring up the interface manually using `ifup <InfiniBand NIC>`



### Provisioning newly added PowerEdge servers in the cluster
To provision newly added servers, wait till the iDRAC IP addresses are automatically added to the *idrac_inventory*. After the iDRAC IP addresses are added, launch the iDRAC template on the AWX UI to provision CentOS custom OS on the servers.  

If you want to re-provision all the servers in the cluster or any of the faulty servers, you must remove the respective iDRAC IP addresses from *provisioned_idrac_inventory* on AWX UI and then launch the iDRAC template. If required, you can delete the *provisioned_idrac_inventory* from the AWX UI to remove the IP addresses of provisioned servers. After the servers are provisioned, *provisioned_idrac_inventory* is created and updated on the AWX UI.

## Configuring Servers with In-Band Management (Provision Method: PXE)

Omnia role used: *provision_cobbler*  
Ports used by Cobbler:  
* TCP ports: 69,8000, 8008
* UDP ports: 69,4011

To create the Cobbler image, Omnia configures the following:
* Firewall settings.
* The kickstart file of Cobbler to enable the UEFI PXE boot.

To access the Cobbler dashboard, enter `https://<IP>/cobbler_web` where `<IP>` is the Global IP address of the control plane. For example, enter
`https://100.98.24.225/cobbler_web` to access the Cobbler dashboard.

>>__Note__: After the Cobbler Server provisions the operating system on the servers, IP addresses and hostnames are assigned by the DHCP service.  
>>* If a mapping file is not provided, the hostname to the server is provided based on the following format: **computexxx-xxx** where "xxx-xxx" is the last two octets of the Host IP address. For example, if the Host IP address is 172.17.0.11 then the assigned hostname by Omnia is compute0-11.  
>>* If a mapping file is provided, the hostnames follow the format provided in the mapping file.  

>>__Note__: If you want to add more nodes, append the new nodes in the existing mapping file. However, do not modify the previous nodes in the mapping file as it may impact the existing cluster.

>> __Note__: With the addition of Multiple profiles, the cobbler container dynamically updates the mount point based on the value of `provision_os` in `base_vars.yml`.

### DHCP routing using Cobbler
Omnia now supports DHCP routing via Cobbler. To enable routing, update the `primary_dns` and `secondary_dns` in `base_vars` with the appropriate IPs (hostnames are currently not supported). For compute nodes that are not directly connected to the internet (ie only host network is configured), this configuration allows for internet connectivity.


## Security enhancements  
Omnia provides the following options to enhance security on the provisioned PowerEdge servers:
* **System lockdown mode**: To enable the system lockdown mode on iDRAC, set the *system_lockdown* variable to "enabled" in the `idrac_vars.yml` file.
* **Secure boot mode**: To enable the secure boot mode on iDRAC, set the *uefi_secure_boot* variable to "enabled" in the `idrac_vars.yml` file.
* **2-factor authentication (2FA)**: To enable the 2FA on iDRAC, set the *two_factor_authentication* variable to "enabled" in the `idrac_vars.yml` file.  
	
	**WARNING**: If 2FA is enabled on iDRAC, you must manually disable 2FA on iDRAC by setting the *Easy 2FA State* to "Disabled" for the user specified in the `login_vars.yml` file to run other iDRAC playbooks. 
	
* Before executing the **idrac_2fa.yml**, you must edit the `idrac_tools_vars.yml` by running the following command: `ansible-vault edit idrac_tools_vars.yml --vault-password-file .idrac_vault_key`.   
* Provide the relevant details in the **idrac_2fa.yml** file. (Information provided in the Parameter Guide) 
>> **Note**: 2FA will be enabled on the iDRAC only if SMTP server details are valid and a test email notification is working using SMTP.  
* **LDAP Directory Services**: To enable or disable the LDAP directory services, set the *ldap_directory_services* variable to "enabled" in the `idrac_vars.yml` file.  
* Before executing the **idrac_ldap.yml** file, you must edit `idrac_tools_vars.yml` by running the following command: `ansible-vault edit idrac_tools_vars.yml --vault-password-file .idrac_vault_key`.  
		* Provide the following values in the **idrac_ldap.yml** file.  
		* To view the `idrac_tools_vars.yml` file, run the following command: `ansible-vault view idrac_tools_vars.yml --vault-password-file .idrac_vault_key`  
	
>>**Note**: It is suggested that you use the ansible-vault view or edit commands and that you do not use the ansible-vault decrypt or encrypt commands. If you have used the ansible-vault decrypt or encrypt commands, provide 644 permission to `idrac_tools_vars.yml`.  

On the AWX Dashboard, select the respective security requirement playbook and launch the iDRAC template by performing the following steps.
1. On the AWX Dashboard, under __RESOURCES__ -> __Templates__, select the **idrac_template**.
2. Under the **Details** tab, click **Edit**.
3. In the **Edit Details** page, click the **Playbook** drop-down menu and select **tools/idrac_system_lockdown.yml**, **tools/idrac_secure_boot.yml**, **tools/idrac_2fa.yml**, or **tools/idrac_ldap.yml**.
4. Click **Save**.
5. To launch the iDRAC template with the respective playbook selected, click **Launch**.  

