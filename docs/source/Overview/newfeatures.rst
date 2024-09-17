New Features
============

* The internal OpenLDAP server can now be configured as a proxy server.

* Kubernetes version upgraded to 1.29.5 (Previously 1.26.12).

* Python version upgraded to 3.11 (Previously 3.9).

* Ansible version upgraded to 9.5.1 (Previously 7.7.0).

* Omnia now executes exclusively within a virtual environment created by the ``prereq.sh`` script.

* Added support for NVIDIA container toolkit for NVIDIA accelerators in a Kubernetes cluster.

* Set OS Kernel command-line parameters and/or configure additional NICs on the nodes using a single playbook.

* Sample playbook for a pre-trained Generative AI model - Llama 3.1

* Added support for corporate proxy on RHEL, Rocky Linux, and Ubuntu clusters.

* CSI drivers for Kubernetes access to PowerScale (without SSL certificate)

* Added support for Intel Gaudi 3 accelerators:

    * Software stack installation

    * Accelerator status verification using HCCL, qual.

    * Inventory tagging for the Gaudi accelerators

    * Monitoring for the Gaudi accelerators via:

        * Omnia telemetry
        * iDRAC telemetry

* AI tools:

    * DeepSpeed and Kubeflow as part of Intel Gaudi AI stack
    * Parity for Kserve, Tensorflow, and Jupyterhub
    * vLLM enablement on clusters containing Intel Gaudi nodes