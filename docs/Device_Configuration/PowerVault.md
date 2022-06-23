# Configuring Dell EMC PowerVault Storage  

* Enter the information required in `input_params/base_vars.yml`, `input_params/login_vars.yml` and `input_params/powervault_vars` per the provided [Input Parameter Guides](../Input_Parameter_Guide/Control_Plane_Parameters).
* Ensure that there's a dedicated data connection between the Storage array and the PowerVault NFS node.

### Run `Powervault_template` via CLI
1. Verify that `/opt/omnia/powervault_inventory` is created and updated with all powervault IP details. This is done automatically when `control_plane.yml` is run. If it's not updated, run `ansible-playbook collect_device_info.yml` (dedicated NIC) or `ansible-playbook collect_node_info.yml` (LOM NIC) from the control_plane directory.
2. Run `ansible-playbook powervault.yml -i /opt/omnia/powervault_inventory`

## Run `Powervault_template` on the AWX UI.
1. Run `kubectl get svc -n awx`.
2. Copy the Cluster-IP address of the awx-ui. 
3. To retrieve the AWX UI password, run `kubectl get secret awx-admin-password -n awx -o jsonpath="{.data.password}" | base64 --decode`.
4. Open the default web browser on the control plane and enter `http://<IP>:8052`, where IP is the awx-ui IP address and 8052 is the awx-ui port number. Log in to the AWX UI using the username as `admin` and the retrieved password.  
5. Under __RESOURCES__ -> __Templates__, launch the **powervault_template**.