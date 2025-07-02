Prerequisites
===============

For the ``local_repo.yml`` playbook to work seamlessly, ensure that the following prerequisites have been met before playbook execution:

1. Ensure that the ``omnia_core`` container is up and running.
2. The OIM should have access to the public network, in order to download and store the packages/images to the desired NFS share.
3. Ensure that all required certificates are stored using **Ansible Vault**, which ensures complete confidentiality and integrity within the cluster.
4. Ensure that the repository URLs for the software packages is accessible. If not, download will fail for that specific package.