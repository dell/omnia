Configure a proxy server for the Control Plane (OIM)
======================================================

Omnia users can now configure a proxy server for the Control Plane. This means that the Control Plane will not have direct access to internet but via a proxy server. To set up the control plane with a proxy server, do the following:

1. Go to ``omnia/input`` folder.

2. Open the ``site_config.yml`` file and add the proxy server details to the ``proxy`` variable, as explained below:

+-----------------------------+-------------------------------------------------------------------------------------------------------------------------------+
| Parameter                   |     Description                                                                                                               |
+=============================+===============================================================================================================================+
| **http_proxy**              |     * This variable points to the HTTP proxy server and the port associated with the proxy server.                            |
|   (Optional)                |     * **Example:** ``"http://corporate-proxy:3128"``                                                                          |
+-----------------------------+-------------------------------------------------------------------------------------------------------------------------------+
| **http_proxy**              |     * This variable points to the HTTPS proxy server and the port associated with the proxy server.                           |
|   (Optional)                |     * **Example:** ``"https://corporate-proxy:3128"``                                                                         |
+-----------------------------+-------------------------------------------------------------------------------------------------------------------------------+
| **no_proxy**                |     * Mandatory if the control plane is behind a proxy server.                                                                |
|   (Optional)                |     * This variable is configured with the control plane hostname and the admin network IP.                                   |
|                             |     * This value is required to exclude the internal cluster network from the proxy server.                                   |
|                             |     * **Example:** ``controlplane.omnia.test,10.5.0.0/16``                                                                    |
+-----------------------------+-------------------------------------------------------------------------------------------------------------------------------+

3. Configure the ``http_proxy`` and ``https_proxy`` environment variables on the control plane server. Run the following commands: ::

       export http_proxy=http://<Control Plane IP>:<port>
       export https_proxy=http://<Control Plane IP>:<port>
       export no_proxy="<Control Plane hostname>","<Admin Network IP>"