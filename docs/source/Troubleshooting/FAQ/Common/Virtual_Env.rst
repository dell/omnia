Virtual environment
=====================

⦾ **What to do if the prereq.sh script execution doesn't activate the Python virtual environment?**

**Potential Cause**: Incorrect syntax used while executing the ``prereq.sh`` script.

**Resolution**:

* Ensure to use ``source prereq.sh`` instead of ``./prereq.sh`` while executing the prereq script. For more information, `click here <../../../OmniaInstallGuide/Ubuntu/Prereq.sh/index.html>`_.
* Even after executing ``./prereq.sh``, you can activate the Python virtual environment using the following command: ::

    source /opt/omnia_venv_1_7/bin/deactivate