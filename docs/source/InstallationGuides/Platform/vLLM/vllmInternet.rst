vLLM container internet enablement
-----------------------------------

To enable internet access within the container, user needs to export ``http_proxy`` and ``https_proxy`` environment variables in the following format

::

    export http_proxy=http://cp-ip:3128
    export https_proxy=http://cp-ip:3128