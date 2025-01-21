Network
========

⦾ **Why does the** ``TASK [infiniband_switch_config : Authentication failure response]`` **fail with the message:** ``Status code was -1 and not [302]: Request failed: <urlopen error [Errno 111] Connection refused>`` **on Infiniband Switches when executing** ``infiniband_switch_config.yml`` **playbook?**

**Potential Cause**: To configure a new Infiniband Switch, HTTP and JSON gateway must be enabled. To verify that they are enabled, run:

* Check if HTTP is enabled: ``show web``

* Check if JSON Gateway is enabled: ``show json-gw``

**Resolution**: To correct the issue, run:

* Enable the HTTP gateway: ``web http enable``

* Enable the JSON gateway: ``json-gw enable``

⦾ **During consecutive runs of the** ``server_spec_update.yml`` **playbook, the additional NICs may not be configured according to the inputs provided in the** ``input/server_spec.yml`` **file, or any unexpected behavior may occur.**

**Potential Cause**: Omnia does not support modifying the category definitions (for example, ``nic_name``, ``nicnetwork``, or ``nictype``) in ``input/server_spec.yml`` or changing the category details in the inventory file provided, during consecutive runs of the ``server_spec_update.yml`` playbook.

**Resolution**: Re-provision the nodes.
