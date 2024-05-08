Updating kernels on RHEL (with subscription)
============================================

**Pre-requisites**

1. Subscription should be available on nodes.

2. Kernels to be upgraded should be available. To verify the status of the kernels, use ``yum list kernel``.

3. The input kernel revision cannot be a RHEL 7.x supported kernel version. e.g. “3.10.0-54.0.1” to “3.10.0-1160”.

4. Input needs to be passed during execution of the playbook.

**Executing the Kernel Upgrade:**

Via CLI: ::

    cd omnia/utils
    ansible-playbook kernel_upgrade.yml -i inventory -e rhsm_kernel_version=x.xx.x-xxxx

Where the inventory refers to a file listing all manager and compute nodes per the format provided in `inventory file <../samplefiles.html>`_. The inventory file is case-sensitive. Follow the casing provided in the sample file link.

