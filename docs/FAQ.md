# Frequently Asked Questions


## Why is the error "Wait for AWX UI to be up" displayed when `control_plane.yml` fails?  
Potential Causes: 
1. AWX is not accessible even after five minutes of wait time. 
2. __isMigrating__ or __isInstalling__ is seen in the failure message.
	
Resolution:  
Wait for AWX UI to be accessible at http://\<management-station-IP>:8081, and then run the `control_plane.yml` file again, where __management-station-IP__ is the IP address of the management node.

## What to do if the nodes in a Kubernetes cluster reboot?  
Wait for 15 minutes after the Kubernetes cluster reboots. Next, verify the status of the cluster using the following commands:
* `kubectl get nodes` on the manager node to get the real-time k8s cluster status.  
* `kubectl get pods --all-namespaces` on the manager node to check which the pods are in the **Running** state.
* `kubectl cluster-info` on the manager node to verify that both the k8s master and kubeDNS are in the **Running** state.

## What to do when the Kubernetes services are not in the __Running__  state?  
1. Run `kubectl get pods --all-namespaces` to verify that all pods are in the **Running** state.
2. If the pods are not in the **Running** state, delete the pods using the command:`kubectl delete pods <name of pod>`
3. Run the corresponding playbook that was used to install Kubernetes: `omnia.yml`, `jupyterhub.yml`, or `kubeflow.yml`.

## What to do when the JupyterHub or Prometheus UI is not accessible?  
Run the command `kubectl get pods --namespace default` to ensure **nfs-client** pod and all Prometheus server pods are in the **Running** state. 

## While configuring Cobbler, why does the `control_plane.yml` fail during the Run import command?  
Cause:
* The mounted .iso file is corrupt.
	
Resolution:
1. Go to __var__->__log__->__cobbler__->__cobbler.log__ to view the error.
2. If the error message is **repo verification failed**, the .iso file is not mounted properly.
3. Verify that the downloaded .iso file is valid and correct.
4. Delete the Cobbler container using `docker rm -f cobbler` and rerun `control_plane.yml`.

## Why does PXE boot fail with tftp timeout or service timeout errors?  
Potential Causes:
* RAID is configured on the server.
* Two or more servers in the same network have Cobbler services running.  

Resolution:  
1. Create a Non-RAID or virtual disk on the server.  
2. Check if other systems except for the management node have cobblerd running. If yes, then stop the Cobbler container using the following commands: `docker rm -f cobbler` and `docker image rm -f cobbler`.

## What to do when the Slurm services do not start automatically after the cluster reboots?  

* Manually restart the slurmd services on the manager node by running the following commands:
```
systemctl restart slurmdbd
systemctl restart slurmctld
systemctl restart prometheus-slurm-exporter
```
* Run `systemctl status slurmd` to manually restart the following service on all the compute nodes.

## Why do Slurm services fail? 

Potential Cause: The `slurm.conf` is not configured properly. 
 
Recommended Actions:
1. Run the following commands:
```
slurmdbd -Dvvv
slurmctld -Dvvv
```
2. Refer the `/var/lib/log/slurmctld.log` file for more information.

## What causes the "Ports are Unavailable" error?

Cause: Slurm database connection fails.  

Recommended Actions:
1. Run the following commands:
```
slurmdbd -Dvvv
slurmctld -Dvvv
```
2. Refer the `/var/lib/log/slurmctld.log` file.
3. Check the output of `netstat -antp | grep LISTEN` for  PIDs in the listening state.
4. If PIDs are in the **Listening** state, kill the processes of that specific port.
5. Restart all Slurm services:

`slurmctl restart slurmctld` on manager node

`systemctl restart slurmdbd` on manager node

`systemctl restart slurmd` on compute node

		
## Why do Kubernetes Pods stop communicating with the servers when the DNS servers are not responding?

Potential Cause: The host network is faulty causing DNS to be unresponsive
 
Resolution:
1. In your Kubernetes cluster, run `kubeadm reset -f` on all the nodes.
2. On the management node, edit the `omnia_config.yml` file to change the Kubernetes Pod Network CIDR. The suggested IP range is 192.168.0.0/16. Ensure that the IP provided is not in use on your host network.
3. Execute omnia.yml and skip slurm `ansible-playbook omnia.yml --skip-tags slurm`

## Why does pulling images to create the Kubeflow timeout causing the 'Apply Kubeflow Configuration' task to fail?
  
Potential Cause: Unstable or slow Internet connectivity.  
Resolution:
1. Complete the PXE booting/format the OS on the manager and compute nodes.
2. In the omnia_config.yml file, change the k8s_cni variable value from `calico` to `flannel`.
3. Run the Kubernetes and Kubeflow playbooks.  

## Why is permission denied when executing the `idrac.yml` file or other .yml files from AWX?
Potential Cause: The "PermissionError: [Errno 13] Permission denied" error is displayed if you have used the ansible-vault decrypt or encrypt commands.  
Resolution:

* Update permissions on the relevant .yml using `chmod 664 <filename>.yml`

It is recommended that the ansible-vault view or edit commands are used and not the ansible-vault decrypt or encrypt commands.

## What to do if the LC is not ready?
* Ensure the LC is in a ready state for all the servers.
* Command to check lc is busy or not: `racadm getremoteservicesstatus`
* Launch iDRAC template.

## What to do if the network CIDR entry of iDRAC IP in /etc/exports file is missing?
* Add an additional network CIDR range of idrac IPs in the */etc/exports* file if the iDRAC IP is not in the management network range provided in base_vars.yml.

## What to do if a custom ISO file is not present on the device?
* Re-run the *control_plane.yml* file.

## What to do if the *management_station_ip.txt* file under *provision_idrac/files* folder is missing?
* Re-run the *control_plane.yml* file.

## Is Disabling 2FA supported by Omnia?
* Disabling 2FA is not supported by Omnia and must be manually disabled.

## Is provisioning server using BOSS controller supported by Omnia?
* Provisioning server using BOSS controller is not supported by Omnia. It will be supported in upcoming releases.

## The provisioning of PowerEdge servers failed. How do I clean up before starting over?
1. Delete the respective iDRAC IP addresses from the *provisioned_idrac_inventory* on the AWX UI or delete the *provisioned_idrac_inventory* to delete the iDRAC IP addresses of all the servers in the cluster.
2. Launch the iDRAC template from the AWX UI.

## What to do when WARNING message regarding older firmware displayed during idrac_template execution and idrac_template task failed?
Potential Cause: Older firmware version in PowerEdge servers. Omnia supports only iDRAC 8 based Dell EMC PowerEdge Servers with firmware versions 2.75.75.75 and above and iDRAC 9 based Dell EMC PowerEdge Servers with Firmware versions 4.40.40.00 and above.

1. Update idrac firmware version in PowerEdge servers manually to the supported version.
2. Re-run idrac_template.
