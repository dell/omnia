Set PXE NICs to Static
-------------------------

Use the below playbook to optionally set all PXE NICs on provisioned nodes to 'static'.

**To run the playbook**::

    cd utils
    ansible-playbook configure_pxe_static.yml -i inventory

Where inventory refers to a list of IPs separated by newlines: ::

    10.5.0.102
    10.5.0.103

