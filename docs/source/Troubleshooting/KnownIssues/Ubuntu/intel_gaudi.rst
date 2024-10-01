Intel Gaudi accelerators
==========================

⦾ **In Kubeflow 1.9, users cannot select Intel Gaudi3 accelerators from the GPU list while creating a new notebook using the JupyterLab's Kubeflow notebook creation UI.**

**Resolution**: Until this issue is addressed in Kubeflow 1.9.1, it's recommended to avoid using notebooks. Instead, use MPIJobs for Gaudi3 accelerators, which functions correctly.