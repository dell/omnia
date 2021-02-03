# Monitor Kuberentes and Slurm
Omnia provides playbooks to configure additional software components for Kubernetes such as JupyterHub and Kubeflow. For workload management (submitting, conrolling, and managing jobs) of HPC, AI, and Data Analytics clusters, you can access Kubernetes and Slurm dashboards and other supported applications. 

__Note:__ To access the below dashboards, user has to login to the manager node and open the installed web browser.

__Note:__ If you are connecting remotely make sure your putty or any other similar client supports X11 forwarding. If you are using mobaxterm version 8 and above, follow the below mentioned steps:
1. `yum install firefox -y`
2. `yum install xorg-x11-xauth`
3. `logout and login back`
4. To launch firefox from terminal use the following command: 
   `firefox&`

## Access Kuberentes Dashboard
1. To verify if the __Kubernetes-dashboard service__ is __running__, run the following command:
  `kubectl get pods --namespace kubernetes-dashboard`
2. To start the Kubernetes dashboard, run the following command:
  `kubectl proxy`
3. From the CLI, run the following command to see the generated tokens: `kubectl get secrets`
4. Copy the token with the name __prometheus-__-kube-state-metrics__ of the type __kubernetes.io/service-account-token__.
5. Run the following command: `kubectl describe secret __<copied token name>__`
6. Copy the encrypted token value.
7. On a web browser(installed on the manager node), enter http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/ to access the Kubernetes Dashboard.
8. Select the authentication method as __Token__.
9. On the Kuberenetes Dashboard, paste the copied encrypted token and click __Sign in__.

## Access Kubeflow Dashboard

__Note:__ Use only port number between __8000-8999__

1. To see which are the ports are in use, use the following command:
   `netstat -an`
2. Choose port number from __8000-8999__ which is not in use.
3. To run the __kubeflow__ dashboard at selected port number, run the following command:
   `kubectl port-forward -n istio-system svc/istio-ingressgateway __selected-port-number__:80`
4. On a web browser installed on the __manager node__, go to http://localhost:selected-port-number/ to launch the kubeflow central navigation dashboard.

## Access JupyterHub Dashboard
If you have installed the JupyterHub application for Kubernetes, you can access the dashboard by following these actions:
1. To verify if the JupyterHub services are running, run the following command: 
   `kubectl get pods --namespace default`
2. Ensure that the pod names starting with __hub__ and __proxy__ are in __running__ status.
3. Run the following command:
   `kubectl get services`
4. Copy the **External IP** of __proxy-public__ service.
5. On a web browser installed on the __manager node__, use the External IP address to access the JupyterHub Dashboard.
6. Enter any __username__ and __password__ combination to enter the Jupyterhub. The __username__ and __password__ can be later configured from the JupyterHub dashboard.

## Prometheus:

* Prometheus is installed in two different ways:
  * Prometheus is installed on the host when Slurm is installed without installing kubernetes.
  * Prometheus is installed as a Kubernetes role, if you install both Slurm and Kubernetes.

If Prometheus is installed as part of k8s role, run the following commands before starting the Prometheus UI:
1. `export POD_NAME=$(kubectl get pods --namespace default -l "app=prometheus,component=server" -o jsonpath="{.items[0].metadata.name}")`
2. `echo $POD_NAME`
3. `kubectl --namespace default port-forward $POD_NAME 9090`

__Note:__ If Prometheus is installed on the host, start the Prometheus web server with the following command:
* Navigate to Prometheus folder. The default path is __/var/lib/prometheus-2.23.0.linux-amd64/__.
* Start the web server, 
  `./prometheus.yml`

Go to http://localhost:9090 to launch the Prometheus UI in the browser.




 






