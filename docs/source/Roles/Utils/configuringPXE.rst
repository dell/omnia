Set PXE NICs to Static
-------------------------

Before provisioning servers, it's important that all PXE NICs are set to static. Omnia includes a utility to achieve this programmatically.

**To run the playbook**::

    cd utils
    ansible-playbook configure_pxe_static.yml -i inventory

Where inventory refers to a list of IPs separated by newlines: ::

    xxx.xxx.xxx.xxx
    yyy.yyy.yyy.yyy

