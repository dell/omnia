After Running the Provision Tool
=================================

Once the servers are provisioned, run the post provision script to:

* configure iDRAC IP or BMC IP (based on input in ``omnia/input/provision_config.yml``).

* configure infiniband IP on remote nodes (based on input in ``omnia/input/provision_config.yml``).

* set hostname for the remote nodes.

* call ``network.yml`` and ``accelerator.yml`` to set up Ethernet switches, Infiniband switches, CUDA toolkit and ROCm drivers.

To run the script, use the below commands: ::

    ansible-playbook post_provision.yml


