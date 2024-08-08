Virtual environment
=====================

⦾ **What to do if the prereq.sh script execution doesn't activate the Python virtual environment?**

.. image:: ../../../images/virtual_env_1.png

**Potential Cause**: Incorrect syntax used while executing the ``prereq.sh`` script.

**Resolution**:

* Executing ``./prereq.sh`` installs all the packages and sets up the virtual environment - but doesn't activate it. You can activate the Python virtual environment using the following command: ::

    source /opt/omnia17_ven/bin/activate

 .. image:: ../../../images/virtual_env_2.png


* To verify that the virtual environment is active, check if the following prompt is displayed: ::

    (omnia) [root@<control_plane_name> omnia]#