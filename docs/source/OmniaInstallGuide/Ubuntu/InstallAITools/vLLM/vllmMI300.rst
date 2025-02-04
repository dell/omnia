vLLM enablement for AMD MI300 GPU
----------------------------------

.. note:: This whole execution will take approximately 3-4 hours.

* MI300 support is enabled with vllm version 0.3.2
* The ``vllm_build.yml`` file is located inside ``omnia/utils/vllm_build``.

Follow the below steps to setup the vLLM:

1. **Build vLLM**

    * Update the ``admin-nic-IP`` in the ``vllm_k8s_config.yml`` file located inside the ``omnia/utils/vllm_build`` directory.

    * Run the ``vllm_build.yml`` playbook using: ::

        ansible-playbook vllm_build.yml

2. **Verify vLLM**

Once the playbook is executed, run the following command to verify whether vLLM image generation was successful.

::

   nerdctl images | grep vllm

3. Update "package" and "tag" details in the ``vllm.json`` file located at ``omnia/tools/input/config/ubuntu/<22.04 or 24.04>/vllm.json``, as shown below.

::

    "vllm_amd": {



        "cluster": [

          {

            "package": "vllm-rocm",

            "tag": "latest",

            "type": "image"

          }

        ]



      }

4. Finally, deploy the latest vllm using the ``vllm.yml`` playbook located at ``omnia/tools/vllm.yml``. Use the following command:

::

    ansible-playbook vllm.yml -i inv.ini

A sample inventory is attached below:

::

    inv.ini

    [kube_node]

    10.5.x.a

    10.5.x.b