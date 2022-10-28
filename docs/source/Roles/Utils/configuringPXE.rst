Set PXE NICs to Static
-------------------------

Use the below playbook to optionally set all PXE NICs on provisioned nodes to 'static'.

**To run the playbook**::

    cd utils
    ansible-playbook configure_pxe_static.yml -i inventory

Where inventory refers to a list of IPs separated by newlines: ::

    xxx.xxx.xxx.xxx
    yyy.yyy.yyy.yyy

