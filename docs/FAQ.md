# Frequently Asked Questions


## Why is the error "Wait for AWX UI to be up" displayed when `control_plane.yml` fails?  
Potential Causes: 
1. AWX is not accessible even after five minutes of wait time. 
2. __isMigrating__ or __isInstalling__ is seen in the failure message.
	
Resolution:  
Wait for AWX UI to be accessible at http://\<management-station-IP>:8081, and then run the `control_plane.yml` file again, where __management-station-IP__ is the IP address of the management node.

## What to do if the nodes in a Kubernetes cluster reboot:
Wait for 15 minutes after the Kubernetes cluster reboots. Next, verify the status of the cluster using the following commands:
* `kubectl get nodes` on the manager node to get the real-time k8s cluster status.  
* `kubectl get pods --all-namespaces` on the manager node to check which the pods are in the **Running** state.
* `kubectl cluster-info` on the manager node to verify that both the k8s master and kubeDNS are in the **Running** state.

## What to do when the Kubernetes services are not in the __Running__  state:
1. Run `kubectl get pods --all-namespaces` to verify that all pods are in the **Running** state.
2. If the pods are not in the **Running** state, delete the pods using the command:`kubectl delete pods <name of pod>`
3. Run the corresponding playbook that was used to install Kubernetes: `omnia.yml`, `jupyterhub.yml`, or `kubeflow.yml`.

## What to do when the JupyterHub or Prometheus UI is not accessible:
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

## What to do when Slurm services do not start automatically after the cluster reboots:

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

## What to do if jobs hang in 'pending' state on the AWX UI:

Run `kubectl rollout restart deployment awx -n awx` from the management station and try to re-run the job.

If the above solution **doesn't work**,
1. Delete all the inventories, groups and organization from AWX UI.
2. Delete the folder: `/var/nfs_awx`.
3. Delete the file: `omnia/control_plane/roles/webui_awx/files/.tower_cli.cfg`.
4. Re-run *control_plane.yml*.
  

## Why is permission denied when executing the `idrac.yml` file or other .yml files from AWX?
Potential Cause: The "PermissionError: [Errno 13] Permission denied" error is displayed if you have used the ansible-vault decrypt or encrypt commands.  
Resolution:

* Update permissions on the relevant .yml using `chmod 664 <filename>.yml`

It is recommended that the ansible-vault view or edit commands are used and not the ansible-vault decrypt or encrypt commands.

## What to do if the LC is not ready:
* Verify that the LC is in a ready state for all servers: `racadm getremoteservicesstatus`
* Launch iDRAC template.

## What to do if the network CIDR entry of iDRAC IP in /etc/exports file is missing:
* Add an additional network CIDR range of idrac IPs in the */etc/exports* file if the iDRAC IP is not in the management network range provided in base_vars.yml.

## What to do if a custom ISO file is not present on the device:
* Re-run the *control_plane.yml* file.

## What to do if the *management_station_ip.txt* file under *provision_idrac/files* folder is missing:
* Re-run the *control_plane.yml* file.

## Is Disabling 2FA supported by Omnia?
* Disabling 2FA is not supported by Omnia and must be manually disabled.

## The provisioning of PowerEdge servers failed. How do I clean up before starting over?
1. Delete the respective iDRAC IP addresses from the *provisioned_idrac_inventory* on the AWX UI or delete the *provisioned_idrac_inventory* to delete the iDRAC IP addresses of all the servers in the cluster.
2. Launch the iDRAC template from the AWX UI.

## What to do if PowerVault throws the error: `Error: The specified disk is not available. - Unavailable disk (0.x) in disk range '0.x-x'`:
1. Verify that the disk in question is not part of any pool: `show disks`
2. If the disk is part of a pool, remove it and try again.

## Why does PowerVault throw the error: `You cannot create a linear disk group when a virtual disk group exists on the system.`?
At any given time only one type of disk group can be created on the system. That is, all disk groups on the system have to exclusively be linear or virtual. To fix the issue, either delete the existing disk group or change the type of pool you are creating.

## Is provisioning server using BOSS controller supported by Omnia?
* Provisioning server using BOSS controller is not supported by Omnia. It will be supported in upcoming releases.


## What to do when iDRAC template execution throws a warning regarding older firmware versions:
Potential Cause: Older firmware version in PowerEdge servers. Omnia supports only iDRAC 8 based Dell EMC PowerEdge Servers with firmware versions 2.75.75.75 and above and iDRAC 9 based Dell EMC PowerEdge Servers with Firmware versions 4.40.40.00 and above.

1. Update iDRAC firmware version in PowerEdge servers manually to the supported version.
2. Re-run idrac_template.

## What steps have to be taken to re-run control_plane.yml after a Kubernetes reset?
1. Delete the folder: `/var/nfs_awx`
2. Delete the file:  `/<project name>/control_plane/roles/webui_awx/files/.tower_cli.cfg`

Once complete, it's safe to re-run control_plane.yml.

## Why does the Initialize Kubeadm task fail with 'nnode.Registration.name: Invalid value: \"<Host name>\"'?

Potential Cause: The control_plane playbook does not support hostnames with an underscore in it such as 'mgmt_station'.

As defined in RFC 822, the only legal characters are the following:
1. Alphanumeric (a-z and 0-9): Both uppercase and lowercase letters are acceptable, and the hostname is case insensitive. In other words, dvader.empire.gov is identical to DVADER.EMPIRE.GOV and Dvader.Empire.Gov.

2. Hyphen (-): Neither the first nor the last character in a hostname field should be a hyphen.

3. Period (.): The period should be used only to delimit fields in a hostname (e.g., dvader.empire.gov)

## What to do when JupyterHub pods are in 'ImagePullBackOff' or 'ErrImagePull' status after executing jupyterhub.yml:
Potential Cause: Your Docker pull limit has been exceeded. For more information, click [here](https://www.docker.com/increase-rate-limits)
1. Delete Jupyterhub deployment by executing the following command in manager node: `helm delete jupyterhub -n jupyterhub`
2. Re-execute jupyterhub.yml after 8-9 hours.

## What to do when Kubeflow pods are in 'ImagePullBackOff' or 'ErrImagePull' status after executing kubeflow.yml:
Potential Cause: Your Docker pull limit has been exceeded. For more information, click [here](https://www.docker.com/increase-rate-limits)
1. Delete Kubeflow deployment by executing the following command in manager node: `kfctl delete -V -f /root/k8s/omnia-kubeflow/kfctl_k8s_istio.v1.0.2.yaml`
2. Re-execute kubeflow.yml after 8-9 hours

## Can Cobbler deploy both Rocky and CentOS at the same time?
No. During Cobbler based deployment, only one OS is supported at a time. If the user would like to deploy both, please deploy one first, **unmount `/mnt/iso`** and then re-run cobbler for the second OS.

## Why do Firmware Updates fail for some components with Omnia 1.1.1?
Due to the latest `catalog.xml` file, Firmware updates fail for some components on server models R640 and R740. Omnia execution doesn't get interrupted but an error gets logged. For now, please download those individual updates manually.

## Why does the Task [network_ib : Authentication failure response] fail with the message 'Status code was -1 and not [302]: Request failed: <urlopen error [Errno 111] Connection refused>' on Infiniband Switches when running `infiniband.yml`?
To configure a new Infiniband Switch, it is required that HTTP and JSON gateway be enabled. To verify that they are enabled, run:

`show web` (To check if HTTP is enabled)

`show json-gw` (To check if JSON Gateway is enabled)

To correct the issue, run:

`web http enable` (To enable the HTTP gateway)

`json-gw enable` (To enable the JSON gateway)


