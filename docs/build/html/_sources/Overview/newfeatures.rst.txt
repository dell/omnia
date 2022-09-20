New Features
===========

- Added support for Red Hat on both control plane and compute nodes
- Added support for BOSS controllers
- Added support for bolt-on BeeGFS configuration
- Added ability to upgrade kernel on Red Hat devices
- Added support for shared LOM (LAN on Motherboard) configuration
- Due to known limitations with AWX, installation of AWX is now optional using the parameter ``awx_web_support``.
- Added LMod module system installation to handle the MODULEPATH Hierarchical problem.
- Added NFS bolt on support to allow manager, compute and login nodes to become NFS clients.
- Added support for PowerVault ME5 over SAS.
- Added NFS server configuration support for PowerVault ME4, ME5.
- Added NVIDIA GPU driver support for RHEL and Rocky.
- Added support for RHEL on AMD servers.