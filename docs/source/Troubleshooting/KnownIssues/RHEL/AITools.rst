AI Tools
=========

⦾ **Kserve deployment occasionally fails on RHEL 8.8 clusters.**

**Potential Cause**: This is a known issue. For more information, check the links attached below:

    1. `Reference 1 <https://github.com/istio/istio/issues/31352>`_
    2. `Reference 2 <https://github.com/istio/istio/issues/22677>`_

**Resolution**: Reprovision the cluster and re-deploy Kserve. The steps to deploy Kserve are located `here <../../../OmniaInstallGuide/Ubuntu/InstallAITools/kserve.html>`_.
