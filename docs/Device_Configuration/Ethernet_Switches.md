# Configuring Ethernet Switches
* Enter the information required in `input_params/base_vars.yml`, `input_params/login_vars.yml`, `ethernet_vars.yml` and/or `input_params/ethernet_tor_vars.yml` per the provided [Input Parameter Guides](../Input_Parameter_Guide/Control_Plane_Parameters/Device_Parameters).

>>**Note**: 
>> * Edit the `ethernet_tor_vars.yml` file for all S3* and S4* PowerSwitches such as S3048-ON, S4048T-ON, S4112F-ON, S4048-ON, S4048T-ON, S4112F-ON, S4112T-ON, and S4128F-ON.  
>> * Edit the `ethernet_vars.yml` file for Dell PowerSwitch S5232F-ON and all other PowerSwitches except S3* and S4* switches.
>> * When initializing a factory reset switch, the user needs to ensure DHCP is enabled and an IPv6 address is not assigned. Omnia will assign an IP address to the switch using DHCP with all other configurations.

## Run `ethernet_template` via CLI
1. Verify that `/opt/omnia/ethernet_inventory` is created and updated with all ethernet switch IP details. This is done automatically when `control_plane.yml` is run. If it's not updated, run `ansible-playbook collect_device_info.yml` (dedicated NIC) or `ansible-playbook collect_node_info.yml` (LOM NIC) from the control_plane directory.
2. Run `ansible-playbook ethernet.yml -i /opt/omnia/ethernet_inventory`

## Run `ethernet_template` via AWX UI
1. Run `kubectl get svc -n awx`.
2. Copy the Cluster-IP address of the awx-ui. 
3. To retrieve the AWX UI password, run `kubectl get secret awx-admin-password -n awx -o jsonpath="{.data.password}" | base64 --decode`.
4. Open the default web browser on the control plane and enter `http://<IP>:8052`, where IP is the awx-ui IP address and 8052 is the awx-ui port number. Log in to the AWX UI using the username as `admin` and the retrieved password.  
5. Under __RESOURCES__ -> __Templates__, launch the **ethernet_template**. 


