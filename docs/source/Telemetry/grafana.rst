Access the Grafana UI
========================

**Prerequisite**

``visualization_support`` should be set to ``true`` during ``prepare_oim.yml`` playbook execution. For more information, `click here <../OmniaInstallGuide/RHEL_new/prepare_oim.html#telemetry-config-yml>`_.

**Steps**

    1. Log in to the Grafana UI via port 5000. Enter the below URL into the browser's address bar: 
    
        ::
        
            http://localhost:5000/login  

        .. note:: In the above command, instead of ``localhost``, you can also provide the admin IP or public IP address to access the Grafana UI.
    
    2. Enter the ``grafana_username`` and ``grafana_password`` as mentioned previously in the ``/opt/omnia/input/project_default/omnia_config_credentials.yml`` input file. Click **Log in**.


        .. image:: ../images/Grafana_login.png
           :width: 600px
        
    
    3. Once you log in to the Grafana UI, go to **Dashboards > Browse** to view all Grafana dashboards available to you.


        .. image:: ../images/Grafana_Dashboards.png
            :width: 600px


    3. Logs of individual containers collected by **Loki** can be viewed by clicking the ``loki`` dashboard, as shown in the below images:


        .. image:: ../images/Grafana_Loki.png
            :width: 600px


        .. role:: raw-role(raw)
            :format: html latex

        :raw-role:`<br/>`


        .. image:: ../images/Loki_logs.png
            :width: 600px


    4. To view the **Data Sources** configured by Omnia, go to **Configuration > Data Sources**. 


        .. image:: ../images/Datasources_Grafana.png
            :width: 600px


        .. role:: raw-role(raw)
            :format: html latex

        :raw-role:`<br/>`


        .. image:: ../images/Datasources_Grafana2.png
            :width: 600px
            

Filter logs using Loki
-----------------------

    1. Log in to the Grafana UI via port 5000. Enter the below URL into the browser's address bar: 
    
        ::
        
            http://localhost:5000/login

        .. note:: In the above command, instead of ``localhost``, you can also provide the admin IP or public IP address to access the Grafana UI.

    2. In the Explore page, select **oim-loki** to view the log browser.

        .. image:: ../images/Grafana_ControlPlaneLoki.png
            :width: 600px

    3. The log browser allows you to filter logs by the job name. Example: 
    
        ::

            { job="Omnia logs"} |= "
            { job="iDRAC Telemetry - idrac_telemetry_receiver container logs"} |= "