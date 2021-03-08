# Monitor Kuberentes and Slurm
Omnia provides playbooks to configure additional software components for Kubernetes such as JupyterHub and Kubeflow. For workload management (submitting, conrolling, and managing jobs) of HPC, AI, and Data Analytics clusters, you can access Kubernetes and Slurm dashboards and other supported applications. 

To access any of the dashboards login to the manager node and open the installed web browser.

If you are connecting remotely ensure your putty or any X11 based clients and you are using mobaxterm version 8 and above, follow the below mentioned steps:

1. To provide __ssh__ to the manager node.
   `ssh -x root@<ip>` (where IP is the private IP of manager node)
2. `yum install firefox -y`
3. `yum install xorg-x11-xauth`
4. `export DISPLAY=:10.0`
5. `logout and login back`
6. To launch firefox from terminal use the following command: 
   `firefox&`

__Note:__ When the putty/mobaxterm session ends, you must run __export DISPLAY=:10.0__ command each time, else Firefox cannot be launched again.

## Setup user account in manager node
1. Login to head node as root user and run `adduser __<username>__`.
2. Run `passwd __<username>__` to set password.
3. Run `usermod -a -G wheel __<username>__` to give sudo permission.

__Note:__ Kuberenetes and Slurm job can be scheduled only for users with __sudo__ privileges.

## Access Kuberentes Dashboard
1. To verify if the __Kubernetes-dashboard service__ is __running__, run `kubectl get pods --namespace kubernetes-dashboard`.
2. To start the Kubernetes dashboard, run `kubectl proxy`.
3. From the CLI, run `kubectl get secrets` to see the generated tokens.
4. Copy the token with the name __prometheus-__-kube-state-metrics__ of the type __kubernetes.io/service-account-token__.
5. Run `kubectl describe secret __<copied token name>__`
6. Copy the encrypted token value.
7. On a web browser(installed on the manager node), enter http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/ to access the Kubernetes Dashboard.
8. Select the authentication method as __Token__.
9. On the Kuberenetes Dashboard, paste the copied encrypted token and click __Sign in__.

## Access Kubeflow Dashboard

It is recommended that you use port numbers between __8000-8999__ and the suggested port number is __8085__.

1. To view the ports which are in use, run the following command:
   `netstat -an`
2. Select a port number between __8000-8999__ which is not in use.
3. To run the **Kubeflow Dashboard** at selected port number, run one of the following commands:  
	`kubectl port-forward -n kubeflow service/centraldashboard __selected_port_number__:80`  
	(Or)  
	`kubectl port-forward -n istio-system svc/istio-ingressgateway __selected_port_number__:80`
4. On a web browser installed on the manager node, go to http://localhost:selected-port-number/ to launch the Kubeflow Central Dashboard.  

For more information about the Kubeflow Central Dashboard, see https://www.kubeflow.org/docs/components/central-dash/overview/.

## Access JupyterHub Dashboard

1. To verify if the JupyterHub services are running, run `kubectl get pods --namespace jupyterhub`.
2. Ensure that the pod names starting with __hub__ and __proxy__ are in __Running__ status.
3. Run `kubectl get services --namespace jupyterhub`.
4. Copy the **External IP** of __proxy-public__ service.
5. On a web browser installed on the __manager node__, use the External IP address to access the JupyterHub Dashboard.
6. Enter any __username__ and __password__ combination to enter the Jupyterhub. The __username__ and __password__ can be later configured from the JupyterHub dashboard.

## Prometheus

Prometheus is installed in two different ways:
  * It is installed on the host when Slurm is installed without installing Kubernetes.
  * It is installed as a Kubernetes role, if you install both Slurm and Kubernetes.

If Prometheus is installed as part of kubernetes role, run the following commands before starting the Prometheus UI:
1. `export POD_NAME=$(kubectl get pods --namespace default -l "app=prometheus,component=server" -o jsonpath="{.items[0].metadata.name}")`
2. `echo $POD_NAME`
3. `kubectl --namespace default port-forward $POD_NAME 9090`

If Prometheus is installed on the host, start the Prometheus web server by run the following command:
1. Navigate to Prometheus folder. The default path is __/var/lib/prometheus-2.23.0.linux-amd64/__.
2. Start the web server, 
  `./prometheus`

Go to http://localhost:9090 to launch the Prometheus UI in the browser.

__Note:__ 
* If Prometheus was installed through slurm without Kubernetes then it will be removed when Kubernetes is installed as Prometheus would be running as a pod. 
* You can use a single instance of Prometheus when both kubernetes and slurm are installed.





 






