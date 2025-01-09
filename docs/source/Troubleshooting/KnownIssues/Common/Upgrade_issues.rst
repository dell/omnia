Upgrade
==========

⦾ **The cryptography software is reporting a security vulnerability after upgrading from Omnia 1.6.1 to 1.7.**

**Potential cause**: This issue occurs if the cryptography version on the login nodes is lower than 44.0.0.

**Resolution**: After upgrading your Omnia OIM from 1.6.1 to 1.7, ensure to update the cryptography version on the login nodes to 44.0.0 using the following command: ::

    pip install cryptography==44.0.0