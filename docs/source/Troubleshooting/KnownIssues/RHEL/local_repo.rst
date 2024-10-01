Local Repositories
======================

⦾ **During the execution of** ``local_repo.yml`` **playbook, if the** ``rhel_os_url`` **parameter in** ``local_repo_config.yml`` **is set to a Red Hat subscription URL, the playbook execution encounters an error and fails while attempting to contact the subscription URL.**

**Potential Cause**: To connect to a Red Hat subscription URL, the local repository configuration needs to include the attributes sslclientkey, sslclientcacert, and sslcacert. However, Omnia does not offer a way for users to input or configure these settings, which leads to connection failures.

**Workaround**: While working with Omnia, the user is expected to provide a RHEL OS URL that does not require a Red Hat subscription.