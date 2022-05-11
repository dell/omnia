# AWX/Ansible Playbooks And How To Use Them

Once `control_plane.yml` is run, AWX UI or Ansible CLI can be used to run different scripts on your control_plane. Some of these functionalities include:
1. [Using `omnia.yml` to set up clusters, BeeGFS etc](INSTALL_OMNIA_CLI.md)
2. [Configure new devices added to the cluster](#configuring-new-devices-added-to-the-cluster)
3. [Assigning Component Roles](#assign-component-roles-using-awx-ui)
4. [Installing JupyterHub And Kubeflow](#install-jupyterhub-and-kubeflow-playbooks)
5. [Assigning Roles to Compute Nodes](#assign-component-roles-using-awx-ui)
6. [Add a new compute node to the cluster](#add-a-new-compute-node-to-the-cluster)
7. [Creating a new cluster](#creating-a-new-cluster)
8. [Updating Kernel on Red Hat](#kernel-updates-on-red-hat)

## Accessing the AWX UI
1. Run `kubectl get svc -n awx`.
2. Copy the Cluster-IP address of the awx-ui.
3. To retrieve the AWX UI password, run `kubectl get secret awx-admin-password -n awx -o jsonpath="{.data.password}" | base64 --decode`.
4. Open the default web browser on the control plane and enter `http://<IP>:8052`, where IP is the awx-ui IP address and 8052 is the awx-ui port number. Log in to the AWX UI using the username as `admin` and the retrieved password.

## Configuring new devices added to the cluster
For Omnia to configure the devices and to provision the bare metal servers which are introduced newly in the cluster, you must configure the corresponding input parameters and deploy the device-specific template from the AWX UI. Based on the devices added to the cluster, click the respective link to go to configuration section.
* [Configure Dell EMC PowerSwitches](../Device_Configuration/Ethernet_Switches.md)
* [Provision OS on PowerEdge Servers](../Device_Configuration/Servers.md)
* [Configure Mellanox InfiniBand Switches](../Device_Configuration/Infiniband_Switches.md)
* [Configure PowerVault Storage](../Device_Configuration/PowerVault.md)


## Assign component roles using AWX UI
1. On the AWX dashboard, under __RESOURCES__ __->__ __Inventories__, select **node_inventory**.
2. Select the **Hosts** tab.
3. To add hosts to the groups, click **+**.
4. Select **Existing Host**, and then select the hosts from the list and add them to the groups--**compute**, **manager**, **login**, or **nfs**.  
   If you have set the `login_node_required` variable in the `omnia_config` file to "false", then you can skip assigning host to the login node.
5. If the login_node_required is true, make sure the hostnames of all the nodes in the cluster especially the manager and login node are in the format: hostname.domainname. For example, manager.omnia.test is a valid FQDN. If the Hostname is not set then freeipa server/client installation will fail.
6. Click __SAVE__.
7. To deploy Kubernetes and Slurm containers on PowerEdge Servers, under __RESOURCES__ -> __Templates__, select **deploy_omnia**, and then click __LAUNCH__.
8. By default, no skip tags are selected, and both Kubernetes and Slurm are deployed.
9. To install only Kubernetes, enter `slurm` and select **slurm**.
10. To install only Slurm, select and add `kubernetes` skip tag.

>> **Note**:
>> * If you would like to skip the NFS client setup, enter `nfs_client` in the skip tag section to skip the **k8s_nfs_client_setup** role of Kubernetes.
>> * For Red Hat Nodes, use AWX to run `redhat_subscription_template` after running `control_plane.yml` to activate red hat subscription. Ensure that the subscription is enabled before assigning component roles (manager, compute, login_node, nfs_node) to the nodes.

15. Click **NEXT**.
16. Review the details in the **PREVIEW** window and click **LAUNCH** to run the DeployOmnia template.

The **deploy_omnia_template** may not run successfully if:
- The **manager** group contains more than one host.
- The **manager**, **compute**, **login**, and **nfs** groups do not contain a host. Ensure that you assign at least one host node to these groups.  
  If you have set the `login_node_required` variable in the `omnia_config` file to "false", then you can skip assigning host to the login node.
- Under Skip Tags, when both kubernetes and slurm tags are selected.

>> __Note__: On the AWX UI, hosts will be listed only after few nodes have been provisioned by Omnia. It takes approximately 10 to 15 minutes to display the host details after the provisioning is complete. If a device is provisioned, but you are unable to view the host details on the AWX UI, then you can run the following command from **omnia** -> **control_plane** -> **tools** folder to view the hosts which are reachable. <br> `ansible-playbook -i ../roles/collect_node_info/provisioned_hosts.yml provision_report.yml`


## Install JupyterHub and Kubeflow playbooks
If you want to install __JupyterHub__ and __Kubeflow__ playbooks, you have to first install the __JupyterHub__ playbook and then install the __Kubeflow__ playbook.  
To install __JupyterHub__ and __Kubeflow__ playbooks:
1.	From AWX UI, under __RESOURCES__ -> __Templates__, select __DeployOmnia__ template.
2.	From __PLAYBOOK__ dropdown menu, select __platforms/jupyterhub.yml__ and launch the template to install JupyterHub playbook.
3.	From __PLAYBOOK__ dropdown menu, select __platforms/kubeflow.yml__ and launch the template to install Kubeflow playbook.

__Note:__ When the Internet connectivity is unstable or slow, it may take more time to pull the images to create the Kubeflow containers. If the time limit is exceeded, the **Apply Kubeflow configurations** task may fail. To resolve this issue, you must redeploy Kubernetes cluster and reinstall Kubeflow by completing the following steps:
1. Complete the PXE booting of the head and compute nodes.
2. In the `omnia_config.yml` file, change the k8s_cni variable value from calico to flannel.
3. Run the Kubernetes and Kubeflow playbooks.

**Note**: If you want to view or edit the `omnia_config.yml` file, run the following command:
- `ansible-vault view omnia_config.yml --vault-password-file .omnia_vault_key` -- To view the file.
- `ansible-vault edit omnia_config.yml --vault-password-file .omnia_vault_key` -- To edit the file.

## Roles assigned to the compute and manager groups
After **DeployOmnia** template is run from the AWX UI, the **omnia.yml** file installs Kubernetes and Slurm, or either Kubernetes or Slurm, as per the selection in the template on the control plane. Additionally, appropriate roles are assigned to the compute and manager groups.

## Add a new compute node to the cluster
If a new node is provisioned through Cobbler, the node address is automatically displayed on the AWX dashboard. The node is not assigned to any group. You can add the node to the compute group along with the existing nodes and run `omnia.yml` to add the new node to the cluster and update the configurations in the manager node.

## Creating a new cluster
From Omnia 1.2, the cobbler container OS will follow the OS on the control plane but will deploy multiple OS's based on the `provision_os` value in `base_vars.yml`.

* When creating a new cluster, ensure that the iDRAC state is not PXE.
* On adding the cluster, run the iDRAC template before running `control_plane.yml`
* If the new cluster is to run on a different OS than the previous cluster, update the parameters `provision_os` and `iso_file_path` in `base_vars.yml`. Then run `control_plane.yml`

>> Example: In a scenario where the user wishes to deploy LEAP and Rocky on their multiple servers, below are the steps they would use:
>> 1. Set `provision_os` to leap and `iso_file_path` to `/root/openSUSE-Leap-15.3-DVD-x86_64-Current.iso`.
>> 2. Run `control_plane.yml` to provision leap and create a profile called `leap-x86_64` in the cobbler container.
>> 3. Set `provision_os` to rocky and `iso_file_path` to `/root/Rocky-8.x-x86_64-minimal.iso`.
>> 4. Run `control_plane.yml` to provision rocky and create a profile called `rocky-x86_64` in the cobbler container.


>> __Note:__ All compute nodes in a cluster must run the same OS. 

## Kernel Updates on Red Hat
### Pre-requisites
1. Subscription should be available on nodes
2. Kernels to be upgraded should be available. To verify the status of the kernels, use `yum list kernel`
3. The input kernel revision cannot be a RHEL 7.x supported kernel version. e.g. “3.10.0-54.0.1” to “3.10.0-1160”.
4. Input needs to be passed during execution of the playbook.

### Executing the Kernel Upgrade:

Via CLI:
`cd omnia/control_plane` <br>
`ansible-playbook kernel_upgrade.yml -i inventory -e rhsm_kernel_version=x.xx.x-xxxx`
Through AWX UI
![img.png](../images/Execute_Kernel_Upgrade_UI.png)

>> **Note:** Omnia does not support roll-backs/downgrades of the Kernel.
