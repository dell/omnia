Telemetry
==========

⦾ **Why does the** ``TASK [orchestrator : Deploy MetalLB IP Address pool]`` **fail?**

.. image:: ../../../images/Metallb_Telemetry_Apptainer_fail.png

**Potential Cause**: ``/var`` partition is full (potentially due to images not being cleared after intel-oneapi images docker images are used to execute benchmarks on the cluster using apptainer support) .

**Resolution**: Clear the ``/var`` partition and retry ``telemetry.yml``.

⦾ **Why does the** ``TASK [grafana : Wait for grafana pod to come to ready state]`` **fail with a timeout error?**

**Potential Cause**: Docker pull limit exceeded.

**Resolution**: Manually input the username and password to your docker account on the control plane.