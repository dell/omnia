Kubernetes
===========

⦾ **Why do Kubernetes Pods show "ImagePullBack" or "ErrPullImage" errors in their status?**

**Potential Cause**: The errors occur when the Docker pull limit is exceeded.
**Resolution**:

    * Ensure that the ``docker_username`` and ``docker_password`` are provided in ``input/provision_config_credentials.yml``.

    * For a HPC cluster, during ``omnia.yml`` execution, a kubernetes secret 'dockerregcred' will be created in default namespace and patched to service account. User needs to patch this secret in their respective namespace while deploying custom applications and use the secret as imagePullSecrets in yaml file to avoid ErrImagePull. `Click here for more info. <https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry>`_

.. note:: If the playbook is already executed and the pods are in **ImagePullBack** state, then run ``kubeadm reset -f`` in all the nodes before re-executing the playbook with the docker credentials.


⦾ **What to do if the nodes in a Kubernetes cluster reboot?**

**Resolution**: Wait for 15 minutes after the Kubernetes cluster reboots. Next, verify the status of the cluster using the following commands:

* ``kubectl get nodes`` on the kube_control_plane to get the real-time kubernetes cluster status.

* ``kubectl get pods  all-namespaces`` on the kube_control_plane to check which the pods are in the **Running** state.

* ``kubectl cluster-info`` on the kube_control_plane to verify that both the kubernetes master and kubeDNS are in the **Running** state.


⦾ **What to do when the Kubernetes services are not in "Running" state:**

**Resolution**:

1. Run ``kubectl get pods  all-namespaces`` to verify that all pods are in the **Running** state.

2. If the pods are not in the **Running** state, delete the pods using the command:``kubectl delete pods <name of pod>``

3. Run the corresponding playbook that was used to install Kubernetes: ``omnia.yml``, ``jupyterhub.yml``, or ``kubeflow.yml``.


⦾ **Why do Kubernetes Pods stop communicating with the servers when the DNS servers are not responding?**

**Potential Cause**: The host network is faulty causing DNS to be unresponsive

**Resolution**:

1. In your Kubernetes cluster, run ``kubeadm reset -f`` on all the nodes.

2. On the management node, edit the ``omnia_config.yml`` file to change the Kubernetes Pod Network CIDR. The suggested IP range is 192.168.0.0/16. Ensure that the IP provided is not in use on your host network.

3. List ``k8s`` in ``input/software_config.json`` and re-run ``omnia.yml``.


⦾ **Why does the 'Initialize Kubeadm' task fail with 'nnode.Registration.name: Invalid value: \"<Host name>\"'?**

**Potential Cause**: The control_plane playbook does not support hostnames with an underscore in it such as 'mgmt_station'.

**Resolution**: As defined in RFC 822, the only legal characters are the following:

1. Alphanumeric (a-z and 0-9): Both uppercase and lowercase letters are acceptable, and the hostname is not case-sensitive. In other words, omnia.test is identical to OMNIA.TEST and Omnia.test.

2. Hyphen (-): Neither the first nor the last character in a hostname field should be a hyphen.

3. Period (.): The period should be used only to delimit fields in a hostname (For example, dvader.empire.gov)