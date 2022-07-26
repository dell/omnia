 # Ansible Playbooks And How To Use Them

Once `control_plane.yml` is run, AWX UI or Ansible CLI can be used to run different scripts on your control_plane. Some of these functionalities include:
1. [Setting up Red Hat Subscription](#red-hat-subscription)
2. [Using `omnia.yml` to set up clusters, BeeGFS etc](INSTALL_OMNIA_CLI.md)
3. [Configure new devices added to the cluster](#configuring-new-devices-added-to-the-cluster)
4. [Installing JupyterHub And Kubeflow](#install-jupyterhub-and-kubeflow-playbooks)
5. [Add a new compute node to the cluster](#add-a-new-compute-node-to-the-cluster)
6. [Creating a new cluster](#creating-a-new-cluster)
7. [Updating Kernel on Red Hat](#kernel-updates-on-red-hat)
8. [Setting up Static IPs on Devices when the network interface type is shared LOM](#setting-up-static-ips-on-devices-when-the-network-interface-type-is-shared-lom)
9. [Setting up a centralized IPA service](#setting-up-a-centralized-ipa-authentication-service)

## Accessing the AWX UI
1. Run `kubectl get svc -n awx`.
2. Copy the Cluster-IP address of the awx-ui.
3. To retrieve the AWX UI password, run `kubectl get secret awx-admin-password -n awx -o jsonpath="{.data.password}" | base64 --decode`.
4. Open the default web browser on the control plane and enter `http://<IP>:8052`, where IP is the awx-ui IP address and 8052 is the awx-ui port number. Log in to the AWX UI using the username as `admin` and the retrieved password.

## Red Hat Subscription
Before running `omnia.yml`, it is mandatory that red hat subscription be set up on compute nodes running Red Hat.
* To set up Red hat subscription, fill in the [rhsm_vars.yml file](../Input_Parameter_Guide/Control_Plane_Parameters/Device_Parameters/rhsm_vars.md). Once it's filled in, run the template using AWX or Ansible. <br>
* The flow of the playbook will be determined by the value of `redhat_subscription_method` in `rhsm_vars.yml`.
    - If `redhat_subscription_method` is set to `portal`, pass the values `username` and `password` on the AWX screen. For CLI, run the command: <br> `ansible-playbook rhsm_subscription.yml -i inventory -e redhat_subscription_username= "<username>" -e redhat_subscription_password="<password>"`
    - If `redhat_subscription_method` is set to `satellite`, pass the values `organizational identifier` and `activation key` on the AWX screen. For CLI, run the command: <br> `ansible-playbook rhsm_subscription.yml -i inventory -e redhat_subscription_activation_key= "<activation-key>" -e redhat_subscription_org_id ="<org-id>"`

## Red Hat Unsubscription
To disable subscription on Red Hat nodes, the `red_hat_unregister_template` has to be called in one of two ways:
1. On AWX, run the template `redhat_unregister_template`. On launching the template, the nodes present in the node inventory will be unregistered from red hat.
2. Using CLI, run the command: `ansible_playbook omnia/control_plane/rhsm_unregister.yml -i inventory`

## Configuring new devices added to the cluster
For Omnia to configure the devices and to provision the bare metal servers which are introduced newly in the cluster, you must configure the corresponding input parameters and deploy the device-specific template from the AWX UI. Based on the devices added to the cluster, click the respective link to go to configuration section.
* [Configure Dell EMC PowerSwitches](../Device_Configuration/Ethernet_Switches.md)
* [Provision OS on PowerEdge Servers](../Device_Configuration/Servers.md)
* [Configure Mellanox InfiniBand Switches](../Device_Configuration/Infiniband_Switches.md)
* [Configure PowerVault Storage](../Device_Configuration/PowerVault.md)


## Assign component roles via AWX UI
1. If Red Hat is used, ensure that red hat subscription is enabled on the nodes. If it isn't, use AWX to run [`redhat_subscription_template`](#red-hat-subscription) after running `control_plane.yml` to activate red hat subscription.
2. On the AWX dashboard, under __RESOURCES__ __->__ __Inventories__, select **node_inventory**.
3. Select the **Hosts** tab.
4. To add hosts to the groups, click **+**.
5. Select **Existing Host**, and then select the hosts from the list and add them to the groups--**compute**, **manager**, **login**, or **nfs**.  
   If you have set the `login_node_required` variable in the `omnia_config` file to "false", then you can skip assigning host to the login node.
6. If the login_node_required is true, make sure the hostnames of all the nodes in the cluster especially the manager and login node are in the format: hostname.domainname. For example, manager.omnia.test is a valid FQDN. If the Hostname is not set then freeipa server/client installation will fail.
7. Click __SAVE__.
8. To deploy Kubernetes and Slurm containers on PowerEdge Servers, under __RESOURCES__ -> __Templates__, select **deploy_omnia**, and then click __LAUNCH__.
9. By default, no skip tags are selected, and both Kubernetes and Slurm are deployed.
10. To install only Kubernetes, enter `slurm` and select **slurm**.
11. To install only Slurm, select and add `kubernetes` skip tag.

>> **Note**:
>> * If you would like to skip the NFS client setup, enter `nfs_client` in the skip tag section to skip the **k8s_nfs_client_setup** role of Kubernetes.

15. Click **NEXT**.
16. Review the details in the **PREVIEW** window and click **LAUNCH** to run the DeployOmnia template.

The **deploy_omnia_template** may not run successfully if:
- The **manager** group contains more than one host.
- The **manager**, **compute**, **login**, and **nfs** groups do not contain a host. Ensure that you assign at least one host node to these groups.  
  If you have set the `login_node_required` variable in the `omnia_config` file to "false", then you can skip assigning host to the login node.
- Under Skip Tags, when both kubernetes and slurm tags are selected.

>> **Note**:
>> On the AWX UI, hosts will be listed only after few nodes have been provisioned by Omnia. It takes approximately 10 to 15 minutes to display the host details after the provisioning is complete. If a device is provisioned, but you are unable to view the host details on the AWX UI, then you can run the following command from **omnia** -> **control_plane** -> **tools** folder to view the hosts which are reachable. <br> `ansible-playbook -i ../roles/collect_node_info/provisioned_hosts.yml provision_report.yml`
>> To set component roles via CLI, refer to [Omnia CLI Installation guide](INSTALL_OMNIA_CLI.md).

## Install JupyterHub and Kubeflow playbooks
If you want to install __JupyterHub__ and __Kubeflow__ playbooks, you have to first install the __JupyterHub__ playbook and then install the __Kubeflow__ playbook.  
To install __JupyterHub__ and __Kubeflow__ playbooks:
1. From AWX UI, under __RESOURCES__ -> __Templates__, select __DeployOmnia__ template.
2. From __PLAYBOOK__ dropdown menu, select __platforms/jupyterhub.yml__ and launch the template to install JupyterHub playbook.
3. From __PLAYBOOK__ dropdown menu, select __platforms/kubeflow.yml__ and launch the template to install Kubeflow playbook.

The same playbooks can also be installed via CLI using:
1. `ansible-playbook platforms/jupyterhub.yml -i inventory`
2. `ansible-playbook platforms/kubeflow.yml -i inventory`

>> **Note**: When the Internet connectivity is unstable or slow, it may take more time to pull the images to create the Kubeflow containers. If the time limit is exceeded, the **Apply Kubeflow configurations** task may fail. To resolve this issue, you must redeploy Kubernetes cluster and reinstall Kubeflow by completing the following steps:
>> 1. Complete the PXE booting of the head and compute nodes.
>> 2. In the `omnia_config.yml` file, change the k8s_cni variable value from calico to flannel.
>> 3. Run the Kubernetes and Kubeflow playbooks.

>> If you want to view or edit the `omnia_config.yml` file, run the following command:
>> - `ansible-vault view omnia_config.yml --vault-password-file .omnia_vault_key` -- To view the file.
>> - `ansible-vault edit omnia_config.yml --vault-password-file .omnia_vault_key` -- To edit the file.

### Roles assigned to the compute and manager groups
After **DeployOmnia** template is run from the AWX UI, the **omnia.yml** file installs Kubernetes and Slurm, or either Kubernetes or Slurm, as per the selection in the template on the control plane. Additionally, appropriate roles are assigned to the compute and manager groups.

## Add a new compute node to the cluster
If a new node is provisioned through Cobbler, the node address is automatically displayed on the AWX dashboard. The node is not assigned to any group. You can add the node to the compute group along with the existing nodes and run `omnia.yml` to add the new node to the cluster and update the configurations in the manager node.

## Creating a new cluster
From Omnia 1.2, the cobbler container OS will follow the OS on the control plane but will deploy multiple OS's based on the `provision_os` value in `base_vars.yml`.

* When creating a new cluster, ensure that the iDRAC state is not PXE.
* On adding the cluster, run the iDRAC template before running `control_plane.yml`
* If the new cluster is to run on a different OS than the previous cluster, update the parameters `provision_os` and `iso_file_path` in `base_vars.yml`. Then run `control_plane.yml`

>> Example: In a scenario where the user wishes to deploy Red Hat and Rocky on their multiple servers, below are the steps they would use:
>> 1. Set `provision_os` to redhat and `iso_file_path` to `/root/rhel-8.5-DVD-x86_64-Current.iso`.
>> 2. Run `control_plane.yml` to provision leap and create a profile called `rhel-x86_64` in the cobbler container.
>> 3. Set `provision_os` to rocky and `iso_file_path` to `/root/Rocky-8.x-x86_64-minimal.iso`.
>> 4. Run `control_plane.yml` to provision rocky and create a profile called `rocky-x86_64` in the cobbler container.


>> **Note**: All compute nodes in a cluster must run the same OS. 

## Setting up Static IPs on Devices when the network interface type is shared LOM
>> **Note**: All steps listed below are to be administered on the control plane. The DHCP provided IPs for these devices will be within the `host_network_range` irrespective of whether `roce_network_nic` is provided.

When the network interface type is set to shared LOM, users can manually assign static IPs to their networking (ethernet or Infiniband) or storage (powervault). Depending on whether the user set up a RoCe network and provided a `roce_network_nic` in `base_vars.yml`, there are two ways users can achieve this:

### When `roce_network_nic` is provided:
1. Get the pod name of the network-config pod: `Kubectl get pods -n network-config`
2. Start a bash shell session with the pod: `kubectl exec -it {{ pod_name }} -n network-config -- /bin/bash `
3. Get the DHCP assigned IP of the device to be configured: `cat /var/lib/dhcp/dhcpd.leases` 
4. Go to AWX > Inventory > <device type> inventory >hosts and add the IP to the inventory.

### When `roce_network_nic` is not provided:
1. Get the pod name of the cobbler pod: `Kubectl get pods -n cobbler`
2. Start a bash shell session with the pod: `kubectl exec -it {{ pod_name }} -n cobbler -- /bin/bash `
3. Get the DHCP assigned IP of the device to be configured: `cat /var/lib/dhcpd/dhcpd.leases` 
4. Go to AWX > Inventory > <device type> inventory >hosts and add the IP to the inventory.


## Kernel Updates on Red Hat
### Pre-requisites
1. Subscription should be available on nodes
2. Kernels to be upgraded should be available. To verify the status of the kernels, use `yum list kernel`
3. The input kernel revision cannot be a RHEL 7.x supported kernel version. e.g. “3.10.0-54.0.1” to “3.10.0-1160”.
4. Input needs to be passed during execution of the playbook.

### Executing the Kernel Upgrade:

Via CLI:
`cd omnia/control_plane` <br>
`ansible-playbook kernel_upgrade.yml -i inventory -e rhsm_kernel_version=x.xx.x-xxxx` <br>
Through AWX UI <br>
![img.png](../images/Execute_Kernel_Upgrade_UI.png)

>>**Note**: Omnia does not support roll-backs/downgrades of the Kernel.

## Setting up a centralized IPA authentication service
IPA services are used to provide account management and centralized authentication. To set up IPA services for all nodes in the target cluster, run the following command from the `omnia/tools` folder on the control plane: <br>
`ansible-playbook install_ipa_client.yml -i inventory -e kerberos_admin_password="" -e ipa_server_hostname="" -e domain_name="" -e ipa_server_ipadress=""` <br>
| Input Parameter         | Definition                                                      | Variable value                                                                                                                                                                                                                                                    |
|-------------------------|-----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| kerberos_admin_password | "admin" user password for the IPA server on RockyOS and RedHat. | The password can be found in the file   `omnia/control_plane/input_params/login_vars.yml` when the IPA server is   installed on the control plane. If the IPA server is installed on the manager   node, the value can be found in `omnia/omnia_config.yml`       |
| ipa_server_hostname     | The hostname of the IPA server                                  | The hostname can be found on the IPA server (typically control plane or   manager node) using the `hostname` command                                                                                                                                              |
| domain_name             | Domain name                                                     | The domain name can be found in the file   `omnia/control_plane/input_params/security_vars.yml` when the IPA server is   installed on the control plane. If the IPA server is installed on the manager   node, the value can be found in `omnia/omnia_config.yml` |
| ipa_server_ipadress     | The IP address of the IPA server                                | The IP address can be found on the IPA server (typically control plane or   manager node) using the `ip a` command. This IP address should be accessible   from all target nodes.                                                                                 |
>> **Note**:
>> * The inventory queried in the above command is to be created by the user prior to running `omnia.yml`.
>> * To set up IPA services on the NFS server,[ click here](../Security/FreeIPA_User_Creation.md#mounting-user-home-directories-to-the-nfs-server)
