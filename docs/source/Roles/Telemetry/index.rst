Telemetry and visualizations
------------------------------

The telemetry feature allows the set up  of Omnia telemetry and/or iDRAC telemetry. It also installs `Grafana <https://grafana.com/>`_ and `Loki <https://grafana.com/oss/loki/>`_ as Kubernetes pods.

To initiate telemetry support, fill out the following parameters in ``omnia/input/telemetry_config.yml``:

.. csv-table:: Parameters
   :file: ../../Tables/telemetry_config.csv
   :header-rows: 1
   :keepspace:

Once you have executed ``provision.yml`` and has also provisioned the cluster, initiate telemetry on the cluster as part of ``omnia.yml``, which configures the cluster with scheduler, storage and authentication using the below command. ::

    ansible-playbook omnia.yml -i inventory

Optionally, you can initiate only telemetry using the below command: ::

    ansible-playbook telemetry.yml -i inventory

.. note:: Depending on the type of telemetry initiated, the following groups are required. :
    omnia_telemetry: manager, compute
    idrac_telemetry: idrac

After initiation, new iDRACs can be added for ``idrac_telemetry`` acquisition by running the following commands: ::

    ansible-playbook add_idrac_node.yml -i inventory

.. note::
    * The passed inventory should have an idrac group.
    * The passed inventory should have an idrac group, if ``idrac_telemetry_support`` is true.
    * If ``omnia_telemetry_support`` is true, then the inventory should have manager and compute groups along with optional login group.
    * Rocky 8.7 is not compatible with the Kubernetes installed by ``monitor.yml`` due to known issues with cri-o. For more information, `click here <https://github.com/cri-o/cri-o/issues/6197>`_.

**To access the Grafana UI**

    i. Find the IP address of the Grafana service using ``kubectl get svc -n grafana``

    .. image:: ../../images/grafanaIP.png

    ii. Login to the Grafana UI by connecting to the cluster IP of grafana service obtained above via port 5000. That is ``http://xx.xx.xx.xx:5000/login``

    .. image:: ../../images/Grafana_login.png

    iii. Enter the ``grafana_username`` and ``grafana_password`` as mentioned in ``monitor/monitor_config.yml``.

    .. image:: ../../images/Grafana_Dashboards.png

    Loki log collections and telemetry/kubernetes dashboards can viewed on the explore section of the grafana UI.

    .. image:: ../../images/Grafana_Loki.png

    Datasources configured by Omnia can be viewed as seen below.

    .. image:: ../../images/Grafana_DataSources.png

**To use Loki for log filtering**

    i. Login to the Grafana UI by connecting to the cluster IP of grafana service obtained above via port 5000. That is ``http://xx.xx.xx.xx:5000/login``

    ii. In the Explore page, select **control-plane-loki**.

    .. image:: ../../images/Grafana_ControlPlaneLoki.png

    iii. The log browser allows users to filter logs by job, node and/or user.

Ex: ::

    (job)= "cluster deployment logs") |= "nodename"
    (job="compute log messages") |= "nodename" |="node_username"



**Visualizations**

.. toctree::

    Visualizations/index




