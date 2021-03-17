# Frequently Asked Questions

* TOC
{:toc}

## Why is the error "Wait for AWX UI to be up" displayed when `appliance.yaml` fails?  
Cause: 
1. When AWX is not accessible even after five minutes of wait time. 
2. When __isMigrating__ or __isInstalling__ is seen in the failure message.
	
Resolution:  
Wait for AWX UI to be accessible at http://\<management-station-IP>:8081, and then run the `appliance.yaml` file again, where __management-station-IP__ is the ip address of the management node.

## What are the next steps after the nodes in a Kubernetes cluster reboots?  
Resolution: 
Wait for upto 15 minutes after the Kubernetes cluster reboots. Next, verify status of the cluster using the following services:
* `kubectl get nodes` on the manager node provides correct k8s cluster status.  
* `kubectl get pods --all-namespaces` on the manager node displays all the pods in the **Running** state.
* `kubectl cluster-info` on the manager node displays both k8s master and kubeDNS are in the **Running** state.

## What to do when the Kubernetes services are not in the __Running__  state?  
Resolution:	
1. Run `kubectl get pods --all-namespaces` to verify the pods are in the **Running** state.
2. If the pods are not in the **Running** state, delete the pods using the command:`kubectl delete pods <name of pod>`
3. Run the corresponding playbook that was used to install Kubernetes: `omnia.yml`, `jupyterhub.yml`, or `kubeflow.yml`.

## What to do when the JupyterHub or Prometheus UI are not accessible?  
Resolution:
Run the command `kubectl get pods --namespace default` to ensure **nfs-client** pod and all prometheus server pods are in the **Running** state. 

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

## What to do when when the error "ports are unavailable" is displayed?
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
Cause: With the host network which is DNS issue.  
Resolution:
1. In your Kubernetes cluster, run `kubeadm reset -f` on the nodes.
2. In the management node, edit the `omnia_config.yml` file to change the Kubernetes Pod Network CIDR. Suggested IP range is 192.168.0.0/16 and ensure you provide an IP which is not in use in your host network.
3. Execute omnia.yml and skip slurm using __skip_ tag __slurm__.

## What to do if time taken to pull the images to create the Kubeflow containers exceeds the limit and the Apply Kubeflow configurations task fails?  
Cause: Unstable or slow Internet connectivity.  
Resolution:
1. Complete the PXE booting/ format the OS on manager and compute nodes.
2. In the omnia_config.yml file, change the k8s_cni variable value from calico to flannel.
3. Run the Kubernetes and Kubeflow playbooks.
