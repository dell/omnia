Granting Kubernetes access
---------------------------

Omnia grants Kubernetes node access to users defined on the kube_control_plane using the ``k8_access.yml`` playbook.

**Prerequisites**

* Ensure the Kubernetes cluster is up and running.
* Update the variable ``user_name``, in the ``input/k8s_access_config.yml`` file with a comma separated list of users.

    +---------------+--------------------------------------------------------------------------------------------+
    | Parameter     | Details                                                                                    |
    +===============+============================================================================================+
    | **user_name** | * A comma-separated list of users to whom access must be granted.                          |
    |               | * Every user defined here must have a home directory configured on the kube_control_plane. |
    | ``String``    |                                                                                            |
    |               | * **Sample values**: ``user1`` or ``user1,user2,user3``.                                   |
    | Required      |                                                                                            |
    +---------------+--------------------------------------------------------------------------------------------+

* Verify that all intended users have a home directory set up on the kube_control_plane.
* Update the ``resources`` and ``verbs`` variables in ``scheduler/roles/k8s_access/template/role.yml.j2`` to customize the access level assigned to the intended users.

    * ``resources`` are a list of kubernetes objects or entities that are used to define, configure, and manage applications or infrastructure within a Kubernetes cluster. Possible values include ``["pods", "services", "deployments", "jobs"]``.
    * ``verbs`` are a list of actions that can be taken on the ``resources``. Possible values are ``["create", "get", "list", "update", "delete"]``.
* The passed inventory should contain a defined ``kube_control_plane``.

::

        [auth_server]

        #node12

        #AI Scheduler: Kubernetes

        [kube_control_plane]

        # node1


        [kube_node]

        # node2

        # node3

        # node4

        # node5

        # node6



To run the playbook, use the below command: ::

    ansible-playbook -i  inventory k8s_access.yml