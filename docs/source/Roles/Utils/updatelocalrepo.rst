Update local repositories (RHEL)
---------------------------------

This playbook updates all local repositories configured on a RHEL cluster after `local repositories have been configured. <../../InstallationGuides/LocalRepo/index.html>_

To run the playbook: ::

    cd utils
    ansible-playbook update_user_repo.yml -i inventory