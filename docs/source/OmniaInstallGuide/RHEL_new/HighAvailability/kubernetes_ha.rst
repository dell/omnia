High Availability (HA) for the Kubernetes cluster
======================================================

Omnia deploys a highly available Kubernetes cluster using the Kubespray container image from the Dell registry. This container contains the Kubespray ansible playbooks, which are used to deploy Kubernetes (k8s) clusters. Kubespray is an open-source tool designed for simplicity and flexibility, ensuring efficient and correct setup of Kubernetes clusters.

Omnia achieves Kubernetes High Availability (HA) by configuring an internal load balancer called `kube-vip <https://kube-vip.io/>`_. Kube-vip is a tool that enables the use of a Virtual IP (VIP) in Kubernetes clusters to support high availability (HA), particularly for services and load balancer setups. In `AddressResolutionProtocol (ARP) <https://wiki.wireshark.org/AddressResolutionProtocol>`_ mode, kube-vip allows Kubernetes cluster nodes to manage traffic routing directly, removing the need for external load balancers and ensuring seamless service availability.

For more information on Kubernetes HA using Kubespray, `click here <https://github.com/kubernetes-sigs/kubespray/blob/master/docs/operations/ha-mode.md>`_.

.. note:: A minimum of 3 provisioned nodes are required to set up Kubernetes HA.

Prerequisites
--------------

* The OIM must have internet connectivity in order to download packages required for cluster deployment and configuration.
* The OIM must have 2 NICs in active state, one for public network and the other for cluster network.
* Ensure that ``prepare_oim.yml`` playbook has executed successfully and all the containers are up and running.
* Ensure that all Kubernetes related packages are available in the Pulp local repository.

Input Parameters
----------------

* Fill up the required parameters for Kubernetes deployment in the ``/opt/omnia/input/project_default/omnia_config.yml`` file. For the complete list of parameters, `click here <../OmniaCluster/schedulerinputparams.html#id1>`_.
* To enable HA, fill up the required parameters in the ``/opt/omnia/input/project_default/high_availability_config.yml`` file. Use the below table as reference:

    .. csv-table:: Parameters for Kubernetes HA
        :file: ../../../Tables/k8s_ha.csv
        :header-rows: 1
        :keepspace:

Sample inventory for HA
---------------------------

::

    [kube_control_plane]
    10.11.0.1
    10.11.0.15
    10.11.0.9

    [etcd]
    10.11.0.3
    10.11.0.7
    10.11.0.8

    [kube_node]
    10.11.0.1
    10.11.0.15
    10.11.0.9

Playbook execution
--------------------

Once all the details are provided to the input files and the Kubespray container image is uploaded to the Dell registry, the ``omnia.yml`` or ``scheduler.yml`` playbook can be executed to deploy the Kubernetes cluster. 

::

    ansible-playbook omnia.yml -i <inventory filepath>

::

    ansible-playbook scheduler.yml -i <inventory filepath>



