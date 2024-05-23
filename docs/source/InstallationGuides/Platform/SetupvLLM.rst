Setup vLLM [^1] yo
-----------------

vLLM is a fast and easy-to-use library for LLM inference and serving. It is seamlessly integrated with popular HuggingFace models. It is also compatible with OpenAI API servers and GPUs (Both NVIDIA and AMD). vLLM 0.2.4 and above supports model inferencing and serving on AMD GPUs with ROCm. At the moment AWQ quantization is not supported in ROCm, but SqueezeLLM quantization has been ported. Data types currently supported in ROCm are FP16 and BF16.

For NVidia, vLLM is a Python library that also contains pre-compiled C++ and CUDA (12.1) binaries.

With an Ansible script, deploy vLLM on both the kube_node and kube_control_plane. After the deployment of vLLM, access the vllm container (AMD GPU) and import the vLLM Python package (NVIDIA GPU). For more information, `click here <https://docs.vllm.ai/en/latest/getting_started/installation.html>`_

**Pre requisites**

* Ensure nerdctl is available on all cluster nodes.

* Only AMD GPUs from the MI200s (gfx90a) are supported.

* For nodes using NVidia, ensure that the GPU has a compute capacity that is higher than 7 (Eg: V100, T4, RTX20xx, A100, L4, H100, etc).

* Ensure the ``kube_node``, ``kube_control_plane`` is setup and working. If NVidia or AMD GPU acceleration is required for the task, install the NVidia (with containerd) or AMD ROCm GPU drivers during provisioning.

* Use ``local_repo.yml`` to create an offline vLLM repository. For more information, `click here. <../../InstallationGuides/LocalRepo/localrepos.html>`_

**[Optional prerequisites]**

* Ensure the system has enough available space. (Approximately 100GiB is required for the vLLM image. Any additional scripting will take disk capacity outside the image.)

* Ensure the passed inventory file has a ``kube_control_plane`` and ``kube_node`` listing all cluster nodes.

* Update the ``/input/software_config.json`` file with the correct vLLM version required. The default value is ``vllm-v0.2.4`` for AMD container and ``vllm latest`` for NVidia.

* Omnia deploys the vLLM pip installation for NVidia GPU, or ``embeddedllminfo/vllm-rocm:vllm-v0.2.4`` container image for AMD GPU.

* Nerdctl does not support mounting directories as devices because it is not a feature of containerd (The runtime that nerdctl uses). Individual files need to be attached while running nerdctl.



**Deploying vLLM**

1. Change directories to the ``tools`` folder: ::

        cd tools

2. Run the ``vllm.yml`` playbook using: ::

    ansible-playbook vllm.yml -i inventory

The default namespace is for deployment is ``vLLM``.

**Accessing the vLLM (AMD)**

1. Verify that the vLLM  image is present in the container engine images: ::

    nerdctl images | grep vllm

2. Run the container image using modifiers to customize the run: ::

    nerdctl run -it --network=host --group-add=video --ipc=host --cap-add=SYS_PTRACE --security-opt seccomp=unconfined --device /dev/kfd  --device /dev/dri/card0 --device /dev/dri/card1 --device /dev/dri/renderD128 -v /opt/omnia/:/app/model embeddedllminfo/vllm-rocm:vllm-v0.2.4

3. To enable an endpoint, `click here <https://docs.vllm.ai/en/latest/getting_started/quickstart.html>`_.

**Accessing the vLLM (NVidia)**

1. Verify that the vLLM package is installed: ::

        python3.9 -c "import vllm; print(vllm.__version__)"

2. Use the package within a python script as demonstrated in the sample below: ::

            from vllm import LLM, SamplingParams

            prompts = [
                "Hello, my name is",
                "The president of the United States is",
                "The capital of France is",
                "The future of AI is",
            ]

            sampling_params = SamplingParams(temperature=0.8, top_p=0.95)
            llm = LLM(model="mistralai/Mistral-7B-v0.1")

            outputs = llm.generate(prompts, sampling_params)

            # Print the outputs.
            for output in outputs:
                prompt = output.prompt
                generated_text = output.outputs[0].text
                print(f"Prompt: {prompt!r}, Generated text: {generated_text!r}")

3. To enable an endpoint, `click here <https://docs.vllm.ai/en/latest/getting_started/quickstart.html>`_.

[^1] This playbook is supported on Ubuntu 22.04 and RHEL 8.8.


vLLM enablement for AMD MI300
------------------------------

.. note:: This whole execution will take approximately 3-4 hours.

* MI300 support is enabled with vllm version 0.3.2
* The ``vllm_build.yml`` file is located inside ``omnia/utility/vllm_build``.

Follow the below steps to setup the vLLM:

1. **Build vLLM**

Run the ``vllm_build.yml`` playbook using

::

    ansible-playbook vllm_build.yml

2. **Verify vLLM**

Once the playbook is executed, run the following command to verify whether vLLM image generation was successful.

::

   nerdctl images | grep vllm

3. Update "package" and "tag" details in the ``vllm.json`` file located at ``omnia/tools/input/config/ubuntu/22.04/vllm.json``, as shown below.

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

vLLM container internet enablement
-----------------------------------

To enable internet access within the container, user needs to export ``http_proxy`` and ``https_proxy`` environment variables in the following format

::

    export http_proxy=http://cp-ip:3128
    export https_proxy=http://cp-ip:3128

For benchmark testing
----------------------

1. Navigate to ``vllm/benchmarks/`` inside the container.
2. Modify the python files (.py) to perform benchmark testing.

Hugging face environment setup
-------------------------------

Utilize the following command to setup the Hugging face environment variables

::

    nerdctl run -it --network=host --group-add=video --ipc=host --cap-add=SYS_PTRACE --security-opt seccomp=unconfined --device /dev/kfd --device /dev/dri/card0 --device /dev/dri/card1 --device /dev/dri/renderD128 -v /opt/omnia/:/app/model --env "HUGGING_FACE_HUB_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxx" vllm-rocm:latest bash

By default, vLLM automatically retrieves models from HuggingFace. If you prefer to utilize models from ModelScope, please set the environment variable value to ``True`` as shown below,

::

    export VLLM_USE_MODELSCOPE=True

**Quick start**

For a complete list of quick start examples, `click here <https://docs.vllm.ai/en/latest/getting_started/examples/examples_index.html>`_.

**Endpoint**

1. *Using api_server*

    * Execute the following command to enable the ``api_server`` inference endpoint inside the container.

        ::

            python -m vllm.entrypoints.api_server --model facebook/opt-125m

        Expected output

        ::

            INFO 01-17 20:25:21 llm_engine.py:73] Initializing an LLM engine with config: model='meta-llama/Llama-2-13b-chat-hf', tokenizer='meta-llama/Llama-2-13b-chat-hf', tokenizer_mode=auto, revision=None, tokenizer_revision=None, trust_remote_code=False, dtype=torch.float16, max_seq_len=4096, download_dir=None, load_format=pt, tensor_parallel_size=1, quantization=None, seed=0)

            INFO 01-17 20:25:21 tokenizer.py:32] For some LLaMA V1 models, initializing the fast tokenizer may take a long time. To reduce the initialization time, consider using 'hf-internal-testing/llama-tokenizer' instead of the original tokenizer.

            WARNING[XFORMERS]: xFormers can't load C++/CUDA extensions. xFormers was built for:

            PyTorch 2.1.1+cu121 with CUDA 1201 (you have 2.0.1+gita61a294)

            Python 3.10.13 (you have 3.10.13)

            Please reinstall xformers (see https://github.com/facebookresearch/xformers#installing-xformers)

            Memory-efficient attention, SwiGLU, sparse and more won't be available.

            Set XFORMERS_MORE_DETAILS=1 for more details

            MegaBlocks not found. Please install it by `pip install megablocks`.

            STK not found: please see https://github.com/stanford-futuredata/stk

            /opt/conda/envs/py_3.10/lib/python3.10/site-packages/torch/cuda/__init__.py:546: UserWarning: Can't initialize NVML

            warnings.warn("Can't initialize NVML")

            INFO 01-17 20:25:37 llm_engine.py:222] # GPU blocks: 2642, # CPU blocks: 327

            INFO: Started server process [10]

            INFO: Waiting for application startup.

            INFO: Application startup complete.

            INFO: Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)

    * You can also directly execute following command on compute node to enable to ``api_server`` endpoint.

        ::

            nerdctl run -d --network=host --group-add=video --ipc=host --cap-add=SYS_PTRACE --security-opt seccomp=unconfined --device /dev/kfd --device /dev/dri/card0 --device /dev/dri/card1 --device /dev/dri/renderD128 -v /opt/omnia/:/app/model docker.io/embeddedllminfo/vllm-rocm:vllm-v0.2.4 /bin/bash -c 'export http_proxy=http://cp-ip:3128 && export https_proxy=http://cp-ip:3128 && python -m vllm.entrypoints.api_server --model facebook/opt-125m'

    * Once the above command is executed, vllm gets enabled through port 8000. Now, user can utilise endpoint to communicate with the model.

        Endpoint example:

        ::

            kmarks@canihipify2:~$ curl http://localhost:8000/generate \

            -d '{

            "prompt": "San Francisco is a",

            "use_beam_search": true,

            "n": 4,

            "temperature": 0

            }'

        Expected output:

        ::

            {"text":["San Francisco is a city of neighborhoods, each with its own unique character and charm. Here are","San Francisco is a city in California that is known for its iconic landmarks, vibrant","San Francisco is a city of neighborhoods, each with its own unique character and charm. From the","San Francisco is a city in California that is known for its vibrant culture, diverse neighborhoods"]}

    .. note:: Replace ``localhost`` with ``node_ip`` while accessing an external node.

2. *Using open.ai api*

    * **OpenAI-Compatible Server**

        vLLM can be deployed as a server that implements the OpenAI API protocol. This allows vLLM to be used as a drop-in replacement for applications using OpenAI API. By default, it starts the server at http://localhost:8000. You can specify the address with ``--host`` and ``--port`` arguments. The server currently hosts one model at a time (OPT-125M in the command below) and implements list models, create chat completion, and create completion endpoints. We are actively adding support for more endpoints.

    * Run the following command:

        ::

            nerdctl run -it --network=host --group-add=video --ipc=host --cap-add=SYS_PTRACE --security-opt seccomp=unconfined --device /dev/kfd --device /dev/dri/card0 --device /dev/dri/card1 --device /dev/dri/renderD128 -v /opt/omnia/:/app/model docker.io/embeddedllminfo/vllm-rocm:vllm-v0.2.4 /bin/bash -c 'export http_proxy=http://cp-ip:3128 && export https_proxy=http://cp-ip:3128 && python -m vllm.entrypoints.openai.api_server --model facebook/opt-125m'

        Expected output:

        ::

            INFO: Started server process [259]

            INFO: Waiting for application startup.

            INFO: Application startup complete.

            INFO: Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)

    * To install OpenAI, run the following command with root privileges from the host entity.

        ::

            pip install openai

    * Run the following command to invoke the python file:

        ::

            cat vivllmamd.py

        ::

            # Modify OpenAI's API key and API base to use vLLM's API server.

            openai_api_key = "EMPTY"

            openai_api_base = http://localhost:8000/v1

            client = OpenAI(

             api_key=openai_api_key,

             base_url=openai_api_base,

            )


            stream = client.chat.completions.create(

             model="meta-llama/Llama-2-13b-chat-hf",

             messages=[{"role": "user", "content": "Explain the differences betweem Navy Diver and EOD rate card"}],

             max_tokens=4000,

             stream=True,

            )

    * For chunk in stream:

        ::

            if chunk.choices[0].delta.content is not None:

             print(chunk.choices[0].delta.content, end="")

    * Run the following command:

        ::

            python3 vivllmamd.py

        Expected output:

        ::

            Navy Divers and Explosive Ordnance Disposal (EOD) technicians are both specialized careers in the

            ................................................................................[approx 15 lines]

            have distinct differences in their training, responsibilities, and job requirements.