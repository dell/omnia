Setup Jupyterhub
-----------------

Using Helm charts, Omnia can install Jupyterhub on Kubernetes clusters. Once Jupyterhub is deployed, log into the UI to create your own notebook servers. For more information, `click here <https://z2jh.jupyter.org/en/stable/jupyterhub/customization.html>`_.

**Prerequisites**

* Ensure the kubernetes cluster is setup and working.
* Ensure the inventory file includes a ``kube_node`` group listing all cluster nodes.
* Review the ``tools/jupyter_config.yml`` file to ensure that the deployment meets your requirements. If not, modify the file.
* Ensure that a local Jupyterhub repository is created using `the local repository script. <../../InstallationGuides/LocalRepo/index.html>`_
* Omnia deploys the ``quay.io/jupyterhub/k8s-singleuser-sample:3.2.0`` image irrespective of whether the intended notebooks are CPU-only, NVidia GPU, or AMD GPU.  To use a custom image, modify the ``omnia/tools/roles/jupyter_config.yml`` file.
* Ensure that NFS has been deployed on the cluster using ``storage.yml`` followed by ``scheduler.yml`` or ``omnia.yml``. Verify that the required NFS storage provisioner is deployed using the below command: ::

    [root@node3 ~]# kubectl get pod -A
    NAMESPACE              NAME                                                              READY   STATUS             RESTARTS       AGE
    default                nfs-omnia-nfs-subdir-external-provisioner-54785fccd-9mp8z         1/1     Running            1 (12m ago)    3h24m

* Verify that the default storage class is set to nfs_client for dynamic persistent volume provisioning. ::

    [root@node3 ~]# kubectl get storageclass
    NAME                   PROVISIONER                                               RECLAIMPOLICY   VOLUMEBINDINGMODE   ALLOWVOLUMEEXPANSION   AGE
    nfs-client (default)   cluster.local/nfs-omnia-nfs-subdir-external-provisioner   Delete          Immediate           true                   17h


**Deploying Jupyterhub**

1. Change directories to the ``tools`` folder: ::

    cd tools

2. Run the ``jupyterhub.yml`` playbook using: ::

       ansible-playbook jupyterhub.yml -i inventory

.. note:: The default namespace for deployment is ``jupyterhub``.


**Accessing the Jupyterhub UI**

1. Verify that the Jupyterhub service is running using metallb loadbalancer.
2. Find the IP address of the Jupyterhub service using: ::

        root@omnianode0000x:/usr/local# kubectl get svc -A
        NAMESPACE     NAME           TYPE           CLUSTER-IP      EXTERNAL-IP   PORT(S)                  AGE
        default       kubernetes     ClusterIP      xx.xx.xx.xx      <none>        443/TCP                  2d2h
        jupyterhub    hub            ClusterIP      xx.xx.xx.xx      <none>        8081/TCP                 2d2h
        jupyterhub    proxy-api      ClusterIP      xx.xx.xx.xx      <none>        8001/TCP                 2d2h
        jupyterhub    proxy-public   LoadBalancer   xx.xx.xx.xx   xx.xx.xx.xx    80:31134/TCP               2d2h

The IP address is listed against ``proxy-public``.

3. For the first log in, use the Login Node. Ensure the login node has an OS installed with GUI support. Use any browser to log in with user credentials.

.. image:: ../../images/Jupyterhub_Login.png

4. Choose your preferred notebook server option and click **Start**. A pod will be created for the user. Available server options will depend on the user logging in.

.. image:: ../../images/Jupyterhub_UI.png

.. image:: ../../images/Jupyterhub_UI_2.png

**Stopping the Notebook server**

1. Click **File > Hub Control Plane**.
2. Select **Stop Server**.

.. note:: Stopping the notebook server only terminates the user pod. The users data persists and can be accessed by loggin in and starting the notebook server again.

**Redeploy Jupyterhub with new configurations**

1. Update the ``tools/jupyter_config.yml`` file with the new configuration.
2. Re-run the ``jupyterhub.yml`` playbook. ::

        cd tools
        ansible-playbook jupyterhub.yml -i inventory

**Clearing Jupyterhub configuration**

Clear the existing configuration by running the below command: ::

    	kubectl delete ns jupyterhub

