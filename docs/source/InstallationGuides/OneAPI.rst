Install oneAPI for MPI jobs
___________________________

**Pre-requisites**

* An Omnia **slurm** cluster running with at least 2 nodes: 1 manager and 1 compute.

1. Download Intel oneAPI Base Toolkit & Intel oneAPI HPC Toolkit to the control plane.
2. Create the DNF repository file in the ``/temp directory`` as a normal user. ::

        tee > /tmp/oneAPI.repo << EOF
        [oneAPI]
        name=IntelÂ® oneAPI repository
        baseurl=https://yum.repos.intel.com/oneapi
        enabled=1
        gpgcheck=1
        repo_gpgcheck=1
        gpgkey=https://yum.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS.PUB
        EOF

3. Move the newly created oneAPI.repo file to the YUM configuration directory. ::

    /etc/yum.repos.d:
    sudo mv /tmp/oneAPI.repo /etc/yum.repos.d

4. Create a folder in ``/install`` directory. eg., ``intelhpc``.
5. Switch to the ``/install/oneAPI`` folder and execute: ::

    dnf download intel-basekit --resolve --alldeps -y && dnf download intel-hpckit --resolve --alldeps -y

6. Once downloaded, make sure there are >=270~ rpm packages in the ``intelhpc`` directory.
7. Inside the ``intelhpc`` folder, create a file named ``update.otherpkgs.pkglist`` with the contents : ::

    intel-basekit

    intel-hpckit

8. Go to ``/root/omnia/utils/os_package_update`` and edit ``package_update_config.yml``.
9. Run ``package_update.yml`` using : ``ansible-playbook package_update.yml``
10. After execution is completed, you can check the existence of ``intelhpckit`` and ``basekit`` packages on the nodes using: ::

    rpm -qa | grep intel*


