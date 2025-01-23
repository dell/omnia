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

            nerdctl run -d --network=host --group-add=video --ipc=host --cap-add=SYS_PTRACE --security-opt seccomp=unconfined --device /dev/kfd --device /dev/dri/card0 --device /dev/dri/card1 --device /dev/dri/renderD128 -v /opt/omnia/:/app/model docker.io/embeddedllminfo/vllm-rocm:vllm-v0.2.4 /bin/bash -c 'export http_proxy=http://<OIM_IP>:3128 && export https_proxy=http://<OIM_IP>:3128 && python -m vllm.entrypoints.api_server --model facebook/opt-125m'

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

            nerdctl run -it --network=host --group-add=video --ipc=host --cap-add=SYS_PTRACE --security-opt seccomp=unconfined --device /dev/kfd --device /dev/dri/card0 --device /dev/dri/card1 --device /dev/dri/renderD128 -v /opt/omnia/:/app/model docker.io/embeddedllminfo/vllm-rocm:vllm-v0.2.4 /bin/bash -c 'export http_proxy=http://<OIM_IP>:3128 && export https_proxy=http://<OIM_IP>:3128 && python -m vllm.entrypoints.openai.api_server --model facebook/opt-125m'

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