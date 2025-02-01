Setup vLLM
----------

vLLM is a fast and easy-to-use library for LLM inference and serving. It is seamlessly integrated with popular HuggingFace models. It is also compatible with OpenAI API servers and GPUs (both NVIDIA and AMD). vLLM 0.2.4 and above supports model inferencing and serving on AMD GPUs with ROCm. At the moment AWQ quantization is not supported in ROCm, but SqueezeLLM quantization has been ported. Data types currently supported in ROCm are FP16 and BF16.

For NVIDIA, vLLM is a Python library that also contains pre-compiled C++ and CUDA (12.1) binaries.

Omnia deploys vLLM on both the ``kube_node`` and ``kube_control_plane``, using an ansible script. After the deployment of vLLM, access the vLLM container (AMD GPU) and import the vLLM Python package (NVIDIA GPU). For more information, `click here <https://docs.vllm.ai/en/latest/getting_started/installation.html>`_

.. note:: This playbook is supported on the Ubuntu 22.04 or 24.04 OS platforms.

**Prerequisites**

* Ensure nerdctl registry is available on all cluster nodes.

* Only AMD MI200s (gfx90a) and newer GPUs are supported.

* For nodes with NVIDIA GPUs, ensure that the GPU has a minimum compute capability of 7.0 (Volta architecture). Few examples of such NVIDIA GPUs are: T4, A100, L4, H100.

* Ensure the ``kube_node``, ``kube_control_plane`` is setup and running. If NVIDIA or AMD GPU acceleration is required for the task, install the NVIDIA (with containerd) or AMD ROCm GPU drivers during provisioning.

* Use ``local_repo.yml`` to create an offline vLLM repository. For more information, `click here. <../../CreateLocalRepo/localrepos.html>`_

**[Optional prerequisites]**

* Ensure the server has enough available space. (Approximately 100GB is required for the vLLM image. Any additional scripting will take disk capacity outside the image.)

* Ensure the provided inventory file has one ``kube_control_plane`` and all cluster nodes should be listed under ``kube_node``.

* Update the ``/input/software_config.json`` file with the correct vLLM version required. The default value is ``vllm-v0.2.4`` for AMD container and ``vllm latest`` for NVidia.

* Omnia deploys the vLLM pip installation for NVIDIA GPU, or ``embeddedllminfo/vllm-rocm:vllm-v0.2.4`` container image for AMD GPU.

* **nerdctl** does not support mounting directories as devices because it is not a feature of containerd (nerdctl runtime). Individual files need to be attached while running nerdctl.


**Deploying vLLM**

1. Change directories to the ``tools`` folder: ::

        cd tools

2. Run the ``vllm.yml`` playbook using: ::

    ansible-playbook vllm.yml -i inventory

The default namespace is for deployment is ``vLLM``.

.. note:: During the ``vllm.yml`` playbook execution, nodes with AMD or NVIDIA GPUs and drivers will install and test either the ``vllm-AMD`` or ``vllm-Nvidia`` containers, respectively.

**Accessing the vLLM (AMD)**

1. Verify that the vLLM  image is present in the container engine images: ::

    nerdctl images | grep vllm

2. Run the container image using modifiers to customize the run: ::

    nerdctl run -it --network=host --group-add=video --ipc=host --cap-add=SYS_PTRACE --security-opt seccomp=unconfined --device /dev/kfd  --device /dev/dri/card0 --device /dev/dri/card1 --device /dev/dri/renderD128 -v /opt/omnia/:/app/model embeddedllminfo/vllm-rocm:vllm-v0.2.4

3. To enable an endpoint, `click here <https://docs.vllm.ai/en/latest/getting_started/quickstart.html>`_.

**Accessing the vLLM (NVIDIA)**

1. Verify that the vLLM package is installed: ::

        python3.11 -c "import vllm; print(vllm.__version__)"

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

.. toctree::

    vllmintelgaudi
    vllmMI300
    vllmInternet
    benchmarktesting
    HuggingFace

