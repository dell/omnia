Space requirements for the control plane running on RHEL or Rocky Linux OS
=============================================================================

* For all available software packages that Omnia supports: 50GB
* For the complete set of software images (in ``/`` or ``/var`` partition): 500GB
* For storing offline repositories (the file path should be specified in ``repo_store_path`` in ``input/local_repo_config.yml``): 50GB

.. csv-table:: Space requirements for images and packages on control plane
   :file: ../../Tables/RHEL_space_req.csv
   :header-rows: 1
   :keepspace:

.. [1] Space allocated as part of OS repository (.iso). No extra space required.
