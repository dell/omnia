Clearing ports from Omnia
--------------------------

To undo the configurations made by Omnia to switch ports in the event of a reconfiguration or a clean-up, the ``delete_switch_ports.yml`` playbook can be utilized.

Enter the required details in ``utils/provision/switch_based_deletion_config.yml``:

+----------------------+----------------------------------------------------------+
| Parameter            | Details                                                  |
+======================+==========================================================+
| switch_based_details | * JSON list of ports to be cleared   from the Omnia DBs. |
|      ``JSON List``   |                                                          |
|      Required        | * Example: ::                                            |
|                      |                                                          |
|                      |       - { ip: 172.96.28.12, ports:   '1-48,49:3,50' }    |
|                      |                                                          |
|                      | * Example with 2 switches: ::                            |
|                      |                                                          |
|                      |        - { ip: 172.96.28.12, ports: '1-48,49:3,50' }     |
|                      |                                                          |
|                      |        - { ip: 172.96.28.14, ports: '1,2,3,5' }          |
|                      |                                                          |
+----------------------+----------------------------------------------------------+

To run the playbook, use the below commands: ::

    cd utils/provision
    ansible-playbook delete_switch_ports.yml

