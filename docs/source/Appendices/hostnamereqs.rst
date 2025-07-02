Hostname requirements
----------------------

* Hostname should not contain the following characters: ``, (comma)``, ``. (period)``, or ``_ (underscore)``.
* Hostname cannot start or end with a hyphen ``(-)``.
* No upper case characters are allowed in the hostname.
* Hostname cannot start with a number.
* Hostname and domain name (``hostname00000x.domain.xxx``) cumulatively cannot exceed 64 characters. For example, if the ``node_name`` provided in ``input/provision_config.yml`` is 'node', and the ``domain_name`` provided is 'omnia.test', Omnia will set the hostname of a target cluster  node to ``node000001.omnia.test``.