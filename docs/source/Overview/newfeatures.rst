New Features
============

* Omnia now executes exclusively within a virtual environment created by the ``prereq.sh`` script

* Python version upgraded to 3.11 (Previously 3.9)

* Ansible version upgraded to 9.5.1 (Previously 7.7.0)

* Kubernetes version upgraded to 1.29.5 (Previously 1.26.12)

* Added support for Intel Gaudi 3 accelerators: **(This is preliminary code and may change before official release)**

    * Software stack installation

    * Accelerator status verification using `HCCL <https://docs.habana.ai/en/latest/API_Reference_Guides/HCCL_APIs/index.html>`_ and `hl_qual <https://docs.habana.ai/en/latest/Management_and_Monitoring/Qualification_Library/index.html>`_

    * Inventory tagging for the Gaudi accelerators (``compute_gpu_intel``)

    * Monitoring for the Gaudi accelerators via:

        * Omnia telemetry
        * iDRAC telemetry
        * Kubernetes telemetry via Prometheus exporter

* AI tools:

    * DeepSpeed and Kubeflow as part of Intel Gaudi AI stack
    * Parity for Kserve, Tensorflow, and Jupyterhub
    * vLLM enablement on clusters containing Intel Gaudi nodes

* Sample playbook for a pre-trained Generative AI model - Llama 3.1

* Visualization of the Kubernetes and Intel Gaudi metrics using Grafana

* CSI drivers for Kubernetes to access PowerScale storage with an option to enable the SmartConnect feature (without SSL certificates)

* Added support for NVIDIA container toolkit for NVIDIA accelerators in a Kubernetes cluster

* Added support for corporate proxy on RHEL, Rocky Linux, and Ubuntu clusters

* Set OS Kernel command-line parameters and/or configure additional NICs on the nodes using a single playbook

* The internal OpenLDAP server can now be configured as a proxy server














