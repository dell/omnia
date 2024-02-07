Setup vLLM
-----------
Using ansible playbooks, Omnia can install vLLM on the kube_node, and the kube_control_node. Once vLLM is deployed, log into the UI to create your own notebook servers. For more information, `click here <https://docs.vllm.ai/en/latest/getting_started/installation.html>`_.

**Pre requisites**

* Ensure the kube_node, kube_control_node is setup and working. If NVidia or AMD GPU acceleration is required for the task, install the NVidia (CUDA 12.1) or AMD (RocM 5.7) GPU drivers during provisioning.
* Ensure the system has enough available space (Over 55GiB).
* Ensure the passed inventory file has a kube_control_plane listing all cluster nodes.
* Review the ``omnia/tools/vllm_config.yml`` file to ensure the deployment meets your requirements. If not, modify the file.
* Update the ``omnia/input/software_config.json`` file with the correct vLLM version required. The default value is ``vllm-v0.2.4`` for AMD container and ``vllm latest`` for NVidia.
* Omnia deploys the vLLM pip installation for NVidia GPU, or ``embeddedllminfo/vllm-rocm:vllm-v0.2.4`` container image for AMD GPU. To use a custom image, modify the ``omnia/tools/roles/vllm_config.yml`` file. While updating the custom image, ensure all additional pre-requisites are met.
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