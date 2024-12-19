Configure a proxy server for the OIM
========================================

.. note:: You can skip the proxy setup using ``site_config.yml`` input file if you have direct internet access on the OIM.

OIM proxy configuration is now available for Omnia users. This means that the OIM will not have direct access to the internet but via a proxy server. To set up the OIM with a proxy server, do the following:

1. Go to ``omnia/input`` folder.

2. Open the ``site_config.yml`` file and add the proxy server details to the ``proxy`` variable, as explained below:

+-----------------------------+-------------------------------------------------------------------------------------------------------------------------------+
| Parameter                   |     Description                                                                                                               |
+=============================+===============================================================================================================================+
| **http_proxy**              |                                                                                                                               |
|   (Mandatory)               |     * This variable points to the HTTP proxy server and the port associated with the proxy server.                            |
|                             |     * **Example:** ``"http://corporate-proxy:3128"``                                                                          |
+-----------------------------+-------------------------------------------------------------------------------------------------------------------------------+
| **https_proxy**             |                                                                                                                               |
|   (Mandatory)               |     * This variable points to the HTTPS proxy server and the port associated with the proxy server.                           |
|                             |     * **Example:** ``"https://corporate-proxy:3128"``                                                                         |
+-----------------------------+-------------------------------------------------------------------------------------------------------------------------------+
| **no_proxy**                |                                                                                                                               |
|   (Optional)                |     * This variable is configured with the OIM hostname, admin network IP or any internal cluster network.                    |
|                             |     * This value is required to exclude the internal cluster network from the proxy server.                                   |
|                             |     * **Example:** ``controlplane.omnia.test,10.5.0.1``                                                                       |
+-----------------------------+-------------------------------------------------------------------------------------------------------------------------------+

    Sample input: ::

        proxy:
           - { http_proxy: "http://corporate-proxy:3128", https_proxy: "http://corporate-proxy:3128", no_proxy: "controlplane.omnia.test,10.5.0.1" }

3. Configure the ``http_proxy``, ``https_proxy``, and ``no_proxy`` environment variables on the OIM server.

    * Execute the following commands to temporarily update the proxy environment variable: ::

       export http_proxy=http://<Corporate_proxy>:<port>
       export https_proxy=http://<Corporate_proxy>:<port>
       export no_proxy="<Control_plane_hostname>","<Admin_Network_IP>"

    * For persistent proxy, update the ``/etc/environment`` or ``/root/.bashrc`` with the proxy environment details. ::

        http_proxy=http://<Corporate_proxy>:<port>
        https_proxy=http://<Corporate_proxy>:<port>
        no_proxy="<Control_plane_hostname>","<Admin_Network_IP>"

.. caution:: You must configure the proxy environment variables on the OIM before running any Omnia playbooks.