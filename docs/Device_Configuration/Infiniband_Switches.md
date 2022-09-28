# Configuring InfiniBand Switches

In your HPC cluster, connect the Mellanox InfiniBand switches using the Fat-Tree topology. In the fat-tree topology, switches in layer 1 are connected through the switches in the upper layer, i.e., layer 2. And, all the compute nodes in the cluster, such as PowerEdge servers and PowerVault storage devices, are connected to switches in layer 1. With this topology in place, we ensure that a 1x1 communication path is established between the compute nodes. For more information on the fat-tree topology, see [Designing an HPC cluster with Mellanox infiniband-solutions](https://community.mellanox.com/s/article/designing-an-hpc-cluster-with-mellanox-infiniband-solutions).

Omnia uses the server-based Subnet Manager (SM). SM runs in a Kubernetes namespace on the control plane. To enable the SM, Omnia configures the required parameters in the `opensm.conf` file. Based on the requirement, the parameters can be edited.  

>>**Note**: Install the InfiniBand hardware drivers by running the below command:  
>> * `yum groupinstall "Infiniband Support" -y` (For Rocky)

## Setting up a new or factory reset switch

Before running `infiniband.yml`, ensure that SSL Secure Cookies are disabled also HTTP and JSON Gateway need to be enabled on your switch.  This can be verified by running:

`show web`  (To check if SSL Secure Cookies is disabled and HTTP is enabled)

`show json-gw` (To check if JSON Gateway is enabled)

In case any of these services are not in the state required, run:

`no web https ssl secure-cookie enable` (To disable SSL Secure Cookies)

`web http enable` (To enable the HTTP gateway)

`json-gw enable` (To enable the JSON gateway)


When connecting to a new or factory reset switch, the configuration wizard requests to execute an initial configuration:
* **(Recommended)** If the user enters 'no', they still have to provide the admin and monitor passwords. 
* If the user enters 'yes', they will also be prompted to enter the hostname for the switch, DHCP details, IPv6 details, etc.

>>**Note**: When initializing a factory reset switch, the user needs to ensure DHCP is enabled and an IPv6 address is not assigned. Omnia will assign an IP address to the Infiniband switch using DHCP with all other configurations.

## Configuring Mellanox InfiniBand Switches

Enter all relevant parameters for configuring your switches in the following files per the provided [Input Parameter Guides](../Input_Parameter_Guide/Control_Plane_Parameters).:
* base_vars.yml
* opensm.conf (optional)
* ib_vars.yml

### Run `infiniband_template` via CLI
1. Verify that `/opt/omnia/infiniband_inventory` is created and updated with all infiniband switch IP details. This is done automatically when `control_plane.yml` is run. If it's not updated, run `ansible-playbook collect_device_info.yml` (dedicated NIC) or `ansible-playbook collect_node_info.yml` (LOM NIC) from the control_plane directory.
2. Run `ansible-playbook infiniband.yml -i /opt/omnia/infiniband_inventory`


### Run infiniband_template on the AWX UI.
1. Run `kubectl get svc -n awx`.
2. Copy the Cluster-IP address of the awx-ui. 
3. To retrieve the AWX UI password, run `kubectl get secret awx-admin-password -n awx -o jsonpath="{.data.password}" | base64 --decode`.
4. Open the default web browser on the control plane and enter `http://<IP>:8052`, where IP is the awx-ui IP address and 8052 is the awx-ui port number. Log in to the AWX UI using the username `admin` and the retrieved password.  
5. Under __RESOURCES__ -> __Templates__, launch the **infiniband_template**.


