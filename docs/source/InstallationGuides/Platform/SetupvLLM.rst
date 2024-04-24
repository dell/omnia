Setup vLLM
-----------

vLLM is a fast and easy-to-use library for LLM inference and serving. It is seamlessly integrated with popular HuggingFace models. It is also compatible with OpenAI API servers and GPUs (Both NVIDIA and AMD). vLLM 0.2.4 and above supports model inferencing and serving on AMD GPUs with ROCm. At the moment AWQ quantization is not supported in ROCm, but SqueezeLLM quantization has been ported. Data types currently supported in ROCm are FP16 and BF16.

For NVidia, vLLM is a Python library that also contains pre-compiled C++ and CUDA (12.1) binaries.

With an Ansible script, deploy vLLM on both the kube_node and kube_control_plane. After the deployment of vLLM, access the vllm container (AMD GPU) and import the vLLM Python package (NVIDIA GPU). For more information, `click here <https://docs.vllm.ai/en/latest/getting_started/installation.html>`_

.. note:: This playbook was validated using Ubuntu 22.04 and RHEL 8.8.

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


vLLM enablement for AMD MI300
------------------------------

.. note:: This whole execution will take approximately 3-4 hours.

* MI300 support is enabled with vllm version 0.3.2
* The ``vllm_build.yml`` file is located inside ``omnia/utility/vllm_build``.

Follow the below steps to setup the vLLM:

1. **Build vLLM**

    Run the ``vllm_build.yml`` playbook using ::

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

