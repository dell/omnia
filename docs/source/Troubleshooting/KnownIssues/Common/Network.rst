Network
========

⦾ **Why does the Task [infiniband_switch_config : Authentication failure response] fail with the message 'Status code was -1 and not [302]: Request failed: <urlopen error [Errno 111] Connection refused>' on Infiniband Switches when running infiniband_switch_config.yml?**

**Potential Cause**: To configure a new Infiniband Switch, HTTP and JSON gateway must be enabled. To verify that they are enabled, run:

To check if HTTP is enabled: ``show web``

To check if JSON Gateway is enabled: ``show json-gw``

**Resolution**: To correct the issue, run:

To enable the HTTP gateway: ``web http enable``

To enable the JSON gateway: ``json-gw enable``


