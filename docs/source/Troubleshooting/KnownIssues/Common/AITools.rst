AI Tools
=========

⦾ **What to do if pulling the Kserve inference model fails with** ``Unable to fetch image "kserve/sklearnserver:v0.11.2": failed to resolve image to digest: Get "https://index.docker.io/v2/": dial tcp 3.219.239.5:443: i/o timeout.`` **?**

**Resolution**:

1. Edit the kubernetes configuration map: ::

        kubectl edit configmap -n knative-serving config-deployment

2. Add docker.io and index.docker.io as part of the registries-skipping-tag-resolving.

For more information, `click here. <https://github.com/kserve/kserve/issues/3372>`_


⦾ **What to do when Kubeflow pods are in 'ImagePullBackOff' or 'ErrImagePull' status after executing** ``kubeflow.yml`` **playbook?**

**Potential Cause**: Your Docker pull limit has been exceeded. For more information, `click here. <https://www.docker.com/increase-rate-limits>`_

**Resolution**:

1. Delete Kubeflow deployment by executing the following command from the ``kube_control_plane``: ::

 kfctl delete -V -f /root/k8s/omnia-kubeflow/kfctl_k8s_istio.v1.0.2.yaml

2. Re-execute ``kubeflow.yml`` after 8-9 hours


⦾ **What to do if the JupyterHub or Prometheus UI is not accessible?**

**Resolution**: Run the command ``kubectl get pods  namespace default`` to ensure **nfs-client** pod and all Prometheus server pods are in the **Running** state.


⦾ **What to do if JupyterHub pods are in 'ImagePullBackOff' or 'ErrImagePull' status after executing** ``jupyterhub.yml`` **playbook?**

**Potential Cause**: Your Docker pull limit has been exceeded. For more information, `click here <https://www.docker.com/increase-rate-limits>`_.

**Resolution**:

1. Delete Jupyterhub deployment by executing the following command on the ``kube_control_plane``: ::

    helm delete jupyterhub -n jupyterhub

2. Re-execute ``jupyterhub.yml`` after 8-9 hours.


