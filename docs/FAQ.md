# Frequently Asked Questions

## Why is the error "Wait for AWX UI to be up" displayed when `appliance.yml` fails?  
Cause: 
1. When AWX is not accessible even after five minutes of wait time. 
2. When __isMigrating__ or __isInstalling__ is seen in the failure message.
	
Resolution:  
Wait for AWX UI to be accessible at http://\<management-station-IP>:8081, and then run the `appliance.yml` file again, where __management-station-IP__ is the IP address of the management node.

## What are the next steps after the nodes in a Kubernetes cluster reboot?  
Resolution: 
Wait for 15 minutes after the Kubernetes cluster reboots. Next, verify the status of the cluster using the following services:
* `kubectl get nodes` on the manager node provides the correct k8s cluster status.  
* `kubectl get pods --all-namespaces` on the manager node displays all the pods in the **Running** state.
* `kubectl cluster-info` on the manager node displays both k8s master and kubeDNS are in the **Running** state.

## What to do when the Kubernetes services are not in the __Running__  state?  
Resolution:	
1. Run `kubectl get pods --all-namespaces` to verify the pods are in the **Running** state.
2. If the pods are not in the **Running** state, delete the pods using the command:`kubectl delete pods <name of pod>`
3. Run the corresponding playbook that was used to install Kubernetes: `omnia.yml`, `jupyterhub.yml`, or `kubeflow.yml`.

## What to do when the JupyterHub or Prometheus UI is not accessible?  
Resolution:
Run the command `kubectl get pods --namespace default` to ensure **nfs-client** pod and all Prometheus server pods are in the **Running** state. 

## While configuring the Cobbler, why does the `appliance.yml` fail with an error during the Run import command?  
Cause:
* When the mounted .iso file is corrupt.
	
Resolution:
1. Go to __var__->__log__->__cobbler__->__cobbler.log__ to view the error.
2. If the error message is **repo verification failed** then it signifies that the .iso file is not mounted properly.
3. Verify if the downloaded .iso file is valid and correct.
4. Delete the Cobbler container using `docker rm -f cobbler` and rerun `appliance.yml`.

## Why does the PXE boot fail with tftp timeout or service timeout errors?  
Cause:
* When RAID is configured on the server.
* When more than two servers in the same network have Cobbler services running.  

Resolution:  
1. Create a Non-RAID or virtual disk in the server.  
2. Check if other systems except for the management node has cobblerd running. If yes, then stop the Cobbler container using the following commands: `docker rm -f cobbler` and `docker image rm -f cobbler`.

## What to do when the Slurm services do not start automatically after the cluster reboots?  
Resolution: 
* Manually restart the slurmd services on the manager node by running the following commands:
```
systemctl restart slurmdbd
systemctl restart slurmctld
systemctl restart prometheus-slurm-exporter
```
* Run `systemctl status slurmd` to manually restart the following service on all the compute nodes.

## What to do when the Slurm services fail? 
Cause: The `slurm.conf` is not configured properly.  
Resolution:
1. Run the following commands:
```
slurmdbd -Dvvv
slurmctld -Dvvv
```
2. Verify `/var/lib/log/slurmctld.log` file.

## How to resolve the "Ports are unavailable" error?
Cause: Slurm database connection fails.  
Resolution:
1. Run the following commands:
```
slurmdbd -Dvvv
slurmctld -Dvvv
```
2. Verify the `/var/lib/log/slurmctld.log` file.
3. Verify: `netstat -antp | grep LISTEN`
4. If PIDs are in the **Listening** state, kill the processes of that specific port.
5. Restart all Slurm services:
```
slurmctl restart slurmctld on manager node
systemctl restart slurmdbd on manager node
systemctl restart slurmd on compute node
```
		
## What to do if Kubernetes Pods are unable to communicate with the servers when the DNS servers are not responding?  
Cause: With the host network which is a DNS issue.  
Resolution:
1. In your Kubernetes cluster, run `kubeadm reset -f` on the nodes.
2. In the management node, edit the `omnia_config.yml` file to change the Kubernetes Pod Network CIDR. The suggested IP range is 192.168.0.0/16 and ensure that you provide an IP that is not in use in your host network.
3. Execute omnia.yml and skip slurm using __skip_ tag __slurm__.

## What to do if the time taken to pull the images to create the Kubeflow containers exceeds the limit and the Apply Kubeflow configurations task fails?  
Cause: Unstable or slow Internet connectivity.  
Resolution:
1. Complete the PXE booting/ format the OS on the manager and compute nodes.
2. In the omnia_config.yml file, change the k8s_cni variable value from calico to flannel.
3. Run the Kubernetes and Kubeflow playbooks.  

## How to resolve the "Permission denied" error while executing the `idrac.yml` file or other .yml files from AWX?
Cause: The "PermissionError: [Errno 13] Permission denied" error is displayed if you have used the ansible-vault decrypt or encrypt commands.  
Resolution:
* Provide Chmod 644 permission to the .yml files which is missing the required permission. 

It is suggested that you use the ansible-vault view or edit commands and that you do not use the ansible-vault decrypt or encrypt commands.

## What to do if LC is not ready?
Resolution:
* Ensure LC is in a ready state for all the servers.
* Launch iDRAC template.

## What to do if the network CIDR entry of iDRAC IP in /etc/exports file is missing?
Resolution:
* Add additional network CIDR range of idrac IP in the */etc/exports* file if iDRAC IP is not in the management network range provided in base_vars.yml.

## What to do if a custom ISO file is not present in the device?
Resolution:
* Re-run the *control_plane.yml* file.

## What to do if the *management_station_ip.txt* file under *provision_idrac/files* folder is missing?
Resolution:
* Re-run the *control_plane.yml* file.

## Is Disabling 2FA supported by Omnia?
Resolution:
* Disabling 2FA is not supported by Omnia and must be manually disabled.

## The provisioning of PowerEdge servers failed. How to resolve the issue and reprovision the servers?
Resolution:
1. Delete the respective iDRAC IP addresses from the *provisioned_idrac_inventory* on the AWX UI or delete the *provisioned_idrac_inventory* to delete the iDRAC IP addresses of all the servers in the cluster.
2. Launch the iDRAC template from the AWX UI.