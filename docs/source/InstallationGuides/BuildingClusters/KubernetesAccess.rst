Granting Kubernetes access
---------------------------

Omnia grants cluster node access to users defined on the manager node using the ``k8_access.yml`` playbook.

**Prerequisites**

* Ensure the Kubernetes cluster is up and running.
* Update the variable ``user_name``, in the ``input/k8s_access_config.yml`` file with a comma separated list of users.
* Verify that all intended users have a home directory set up on the manager node.
* Update the ``resources`` and ``verbs`` variables in ``scheduler/roles/k8s_access/template/role.yml.j2`` to customize the access level assigned to the intended users.
* The passed inventory should contain a defined ``kube_control_plane``.

To run the playbook, use the below command: ::

    ansible-playbook -i  inventory k8s_access.yml