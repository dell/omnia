Deploy CSI drivers for Dell PowerScale storage solutions
===========================================================

Dell PowerScale is a flexible and secure scale-out NAS (network attached storage) solution designed to simplify storage requirements for AI and HPC workloads. To enable the PowerScale storage solution on the Kubernetes clusters, Omnia installs the Dell CSI PowerScale driver (version 2.11.0) on the nodes using helm charts. Once the PowerScale CSI driver is installed, the PowerScale nodes can be connected to the Kubernetes clusters for storage requirements.
To know more about the CSI PowerScale driver, `click here <https://dell.github.io/csm-docs/docs/deployment/helm/drivers/installation/isilon/>`_.

.. caution:: PowerScale CSI driver installation is only supported on RHEL 8.8, Rocky Linux 8.8, and Ubuntu 22.04 clusters.

.. note:: Omnia doesn't configure any PowerScale device via OneFS (operating system for PowerScale). Omnia configures the deployed Kubernetes cluster to interact with the PowerScale storage.

Prerequisites
--------------

1. Download the ``secret.yaml`` file template from this `link <https://github.com/dell/csi-powerscale/blob/main/samples/secret/secret.yaml>`_.

2. Update the following parameters in the ``secret.yaml`` file as per your cluster details and keep the rest as default values. For example:

    *	clusterName: "omniacluster"
    *	username: "root"
    *	password: "Dell1234"
    *	endpoint: "100.67.170.140"
    *	endpointPort: 8080
    *	isDefault: true
    *	isiPath: "/ifs/data/csi"

   *Reference values from OneFS portal:*

   .. image:: ../../../images/CSI_1.png

3. Download the ``values.yaml`` files template using the following command: ::

    wget https://raw.githubusercontent.com/dell/helm-charts/csi-isilon-2.11.0/charts/csi-isilon/values.yaml

4. Update the following parameters in the ``values.yaml`` file and keep the rest as default values. Refer the below sample values:

    * controllerCount: 1

    * replication:

        enabled: false

    * snapshot:

        enabled: true

    * resizer:

        enabled: false

    * healthMonitor:

        enabled: false

    * endpointPort:8080

    * skipCertificateValidation: true

    * isiAccessZone: System

    * isiPath: /ifs/data/csi


.. note:: In order to integrate PowerScale solution to the deployed Kubernetes cluster, Omnia 1.7 requires the following fixed parameter values in ``values.yaml`` file:

    * controllerCount: 1
    * Replication: false
    * Snapshot: true
    * skipCertificateValidation: true

Installation Process
---------------------

1. Once ``secret.yaml`` and ``values.yaml`` is filled up with the necessary details, copy both files to any directory on the control plane. For example, ``/tmp/secret.yaml`` and ``/tmp/values.yaml``.

2. Add the ``csi_driver_powerscale`` entry along with the driver version to the ``omnia/input/software_config.json`` file: ::

    {"name": "csi_driver_powerscale", "version":"v2.11.0"}

 .. note:: By default, the ``csi_driver_powerscale`` entry is not present in the ``input/software_config.json``.

3. Execute the ``local_repo.yml`` playbook to download the required artifacts to the control plane: ::

    cd local_repo
    ansible-playbook local_repo.yml

4. Add the filepath of the ``secret.yaml`` and ``values.yaml`` file to the ``csi_powerscale_driver_secret_file_path`` and ``csi_powerscale_driver_values_file_path`` variables respectively, present in the ``omnia/input/omnia_config.yml`` file.

5. Execute the ``omnia.yml`` playbook to install the PowerScale CSI driver: ::

    cd omnia
    ansible-playbook omnia.yml -i <inventory_filepath>

.. note::
     * There isn't a separate playbook to run for PowerScale CSI driver installation. Running ``omnia.yml`` with necessary inputs installs the driver. If Kubernetes is already deployed on the cluster, users can also run the ``scheduler.yml`` playbook to install the PowerScale CSI driver.
     * After running ``omnia.yml`` playbook, the ``secret.yaml`` file will be encrypted. User can use below command to decrypt and edit it if required: ::

         ansible-vault edit <secret.yaml filepath> --vault-password-file scheduler/roles/k8s_csi_powerscale_plugin/files/.csi_powerscale_secret_vault

.. caution:: Do not delete the vault key file ``.csi_powerscale_secret_vault``, otherwise users will not be able to decrypt the ``secret.yaml`` file anymore.

Expected Results
------------------

* After the successful execution of the ``omnia.yml`` playbook, the PowerScale CSI drivers are installed on the nodes.
* If there are errors during CSI driver installation, the whole ``omnia.yml`` playbook execution does not stop or fail. It pauses for 10 seconds with CSI driver installation failure error message and then proceeds with rest of the playbook execution.
* For an unsuccessful driver installation scenario, the user first needs to follow the manual removal steps mentioned below from the ``kube_control_plane``, and then re-run the ``omnia.yml`` playbook for CSI driver installation.

Post-requisites
----------------

**Create storage class**:

PowerScale driver installation doesn't create any storage class by default. Users need to create storage class manually post installation of the PowerScale CSI driver. A sample storage class manifest is available `here <https://github.com/dell/csi-powerscale/blob/main/samples/storageclass/isilon.yaml>`_. Use this sample manifest to create a ``StorageClass`` to provision storage; update the manifest as per the requirements.

*Sample storageclass template*: ::

    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata :
      name: ps01
    provisioner: csi-isilon.dellemc.com
    reclaimPolicy: Delete
    allowVolumeExpansion: true
    volumeBindingMode: Immediate
    parameters :
      clusterName: omniacluster
      AccessZone: System
      AzServiceIP: 100.67.170.140
      Isipath: /ifs/data/csi/
      RootClientEnab1ed: "true"
      csi.storage.k8s.io/fstype: "nfs"

**Create Persistent Volume Claim (PVC)**:

Once the storage class is created, the same can be used to create PVC.

*Sample deployment with PVC*: ::

    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: pvc-powerscale
    spec:
      accessModes:
        - ReadWriteMany
      resources:
        requests:
          storage: 1Gi
      storageClassName: ps01
    ---
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: deploy-busybox-01
    spec:
      strategy:
        type: Recreate
      replicas: 1
      selector:
        matchLabels:
          app: deploy-busybox-01
      template:
        metadata:
          labels:
            app: deploy-busybox-01
        spec:
          containers:
            - name: busybox
              image: registry.k8s.io/busybox
              command: ["sh", "-c"]
              args: ["while true; do touch /data/datafile; rm -f /data/datafile; done"]
              volumeMounts:
                - name: data
                  mountPath: /data
              env:
                - name: http_proxy
                  value: "http://100.67.255.254:3128"
                - name: https_proxy
                  value: "http://100.67.255.254:3128"
          volumes:
            - name: data
              persistentVolumeClaim:
                claimName: pvc-powerscale

*Expected Result*:

* Once the above manifest is applied, a PVC is created under name ``pvc-powerscale`` and is in ``Bound`` status. Use the ``kubectl get pvc -A`` command to bring up the PVC information. For example: ::

    root@node001:/opt/omnia/csi-driver-powerscale/csi-powerscale/dell-csi-helm-installer# kubectl get pvc -A
    NAMESPACE   NAME                STATUS   VOLUME           CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
    default     pvc-powerscale      Bound    k8s-b00f77b817   1Gi        RWX            ps01           <unset>                 27h

* User can also verify the same information from the OneFS portal. In the sample image below, it is mapped with the ``VOLUME`` entry from the above example: ``k8s-b00f77b817``:

.. image:: ../../../images/CSI_OneFS.png

Removal
--------

There is no dedicated playbook to remove only the PowerScale CSI driver while keeping Kubernetes cluster intact. Omnia removes the PowerScale CSI driver as part of the ``reset_cluster_configuration.yml`` playbook. This playbook destroys the Kubernetes cluster. For more information on this playbook, `click here <../../Maintenance/reset.html>`_.

To remove the PowerScale driver manually, do the following:

1. Login to the ``kube_control_plane``.

2. Use the following command to bring up the list of all deployments on your cluster: ::

    kubectl get deployment -A

 .. image:: ../../../images/CSI_get_deployment.png

3. Get the name of your CSI deployment and run the following command to delete your deployment: ::

    kubectl delete deployment <CSI deployment name>

 .. image:: ../../../images/CSI_delete_deployment.png

* [Optional] To verify that the deployment has been successfully deleted, run the ``kubectl get deployment -A`` command again after executing the ``kubectl delete`` command. If your ``<CSI deployment name>`` is absent, then the deletion is successful.

4. Use the following command to get the name of your storageclass: ::

    kubectl get storageclass

 .. image:: ../../../images/CSI_get_storageclass.png

5. Run the following command to delete your storageclass: ::

    kubectl delete <storageclass name>

 .. image:: ../../../images/CSI_delete_storageclass.png

* [Optional] To verify that the storageclass has been successfully deleted, run the ``kubectl get storageclass`` command again after executing the ``kubectl delete`` command. If your ``<storageclass name>`` is absent, then the deletion is successful.

6. Execute the following command to switch to the ``dell-csi-helm-installer`` directory: ::

    cd /opt/omnia/csi-driver-powerscale/csi-powerscale/dell-csi-helm-installer

7. Once you're inside the ``dell-csi-helm-installer`` directory, use the following command to trigger the ``csi-uninstall`` script: ::

    ./csi-uninstall.sh --namespace isilon

8. After running the previous command, the PowerScale driver is removed. But, the secret and the created PVC are not removed. Users needs to manually remove them from the ``isilon`` namespace.

.. note:: In case OneFS portal credential changes, users need to perform following steps to update the changes to the ``secret.yaml`` manually:

    1. Update the ``secret.yaml`` file with the changed credentials.
    2. Login and copy the ``secret.yaml`` file to the ``kube_control_plane``.
    3. Delete the existing secret by executing the following command: ::

        kubectl delete secret isilon-creds -n isilon

    4. Create the new secret from the updated ``secret.yaml`` file by executing the following command: ::

        kubectl create secret generic isilon-creds -n isilon --from-file=config=<updated secret.yaml filepath>