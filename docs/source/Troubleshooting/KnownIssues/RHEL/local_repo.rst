Local Repositories
======================

⦾ **During the execution of** ``local_repo.yml`` **playbook, if the** ``rhel_os_url`` **parameter in** ``local_repo_config.yml`` **is set to a Red Hat subscription URL, the playbook execution encounters an error and fails while attempting to contact the subscription URL.**

**Potential Cause**: To connect to a Red Hat subscription URL, the local repository configuration requires Red Hat subscription authentication, which Omnia does not support.

**Workaround**: The user is expected to provide a RHEL OS URL for the ``codereadybuilder`` (CRB) repository that does not require a Red Hat subscription.