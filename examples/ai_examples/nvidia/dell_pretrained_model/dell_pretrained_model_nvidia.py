# Copyright 2024 Dell Inc. or its subsidiaries. All Rights Reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This script allows you to deploy, infer, or delete a Dell authentic 
pretrained model in a Kubernetes cluster for Nvidia Platforms.

Prerequisites:
- Kubernetes (k8s) must be installed and configured on your cluster.
- Nvidia GPU should present in kube node and cuda must be installed.
- Verify PRETRAINED_MODEL_CONFIG section for any changes and 
  update user_HF_token if required by model.
- The Kube control plane needs an active Internet connection. If there is no active Internet 
  connection, you need to set the proxy environment variables to have access to the Internet.
    The proxy environment variables should be set to the IP address of the control plane. 
    For example: 
    export http_proxy=http://<control_plane_ip>:3128 
    export https_proxy=http://<control_plane_ip>:3128 

Usage:
    1. Deploy the model and service:
        python3 dell_pretrained_model_nvidia.py --deploy 

    2. Run an inference using a query, within compute cluster:
        python3 dell_pretrained_model_nvidia.py --infer "<Your_query_here>"

        - If you omit the query string, a default query will be used:
        python3 dell_pretrained_model_nvidia.py --infer

    3. Run an inference using a specific service IP, from outside computer cluster:
        python3 dell_pretrained_model_nvidia.py --infer "<Your_query_here>" 
        --service-ip <pretrained-model-service-ip>

        Note: check service ip on kube control plane using kubectl get svc pretrained-model-service

        - If you omit the query string, a default query will be used with the provided service IP:
        python3 dell_pretrained_model_nvidia.py --infer --service-ip <pretrained-model-service-ip>

    3. Delete the deployed model service:
        python3 dell_pretrained_model_nvidia.py --delete
"""

import subprocess
import time
import argparse
import logging
import sys
import ipaddress
import requests

SERVICE_NAME = "pretrained-model-service" # must be same as defined in PRETRAINED_MODEL_CONFIG
# Define Dell Pretrained Model Deployment config YAML
PRETRAINED_MODEL_CONFIG = """
apiVersion: v1
kind: Service
metadata:
  name: pretrained-model-service
spec:
  type: LoadBalancer
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
  selector:
    app: pretrained-model-app
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pretrained-model-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: pretrained-model-app
  template:
    metadata:
      labels:
        app: pretrained-model-app
        hf.co/model: meta-llama--Meta-Llama-3.1-8b-Instruct
        hf.co/task: text-generation
    spec:
      runtimeClassName: nvidia
      containers:
        - name: pretrained-model-container
          image: registry.dell.huggingface.co/enterprise-dell-inference-meta-llama-meta-llama-3.1-8b-instruct
          resources:
            limits:
              nvidia.com/gpu: 1
          env:
            - name: NUM_SHARD
              value: "1"
            - name: MAX_BATCH_PREFILL_TOKENS
              value: "32768"
            - name: MAX_INPUT_TOKENS
              value: "8000"
            - name: MAX_TOTAL_TOKENS
              value: "8192"
            - name: HF_TOKEN
              value: "user_HF_token"
          volumeMounts:
            - mountPath: /dev/shm
              name: dshm
      volumes:
        - name: dshm
          emptyDir:
            medium: Memory
            sizeLimit: 1Gi
"""

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

K8S_EXCEPTION = "not found"

def run_command(command, input_data=None):
    """
    Runs a shell command and returns the output.
    Args:
        command (str): The shell command to be executed.
        input_data (str, optional): Data to be passed to the command via stdin.
    Returns:
        str: The output of the command.
    Raises:
        RuntimeError: If the command fails.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            input=input_data
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Run Command '{command}' failed with error: {e.stderr.strip()}") from e

def check_kubectl_availability():
    """
    Checks if Kubernetes kubectl is installed and available.
    This function runs `kubectl version --client` to ensure that kubectl is
    installed and can be executed.
    """
    try:
        run_command("kubectl get nodes")
        logging.info("Prerequisites- k8s present.")
    except FileNotFoundError as e:
        logging.error(
            "k8s, kubectl is not available or not configured properly: %s",
            e
            )
        sys.exit(1)
    except RuntimeError as e:
        logging.warning(
            "k8s is not installed and configured. Run omnia.yml to setup K8s in the cluster: %s",
            e
        )
        sys.exit(1)

def check_nvidia_device_plugin_availability():
    """
    Check if the Nvidia device plugin is present in the output of the 'kubectl get pods' command.
    Returns:
        None
    """
    try:
        result = run_command("""kubectl get pods -n nvidia-device-plugin |
         grep -v -e 'gpu-feature-discovery' -e 'node-feature-discovery'""")
        if "nvidia-device-plugin" not in result:
            logging.warning(
            "Nvidia device plugin is not present, Run omnia.yml to setup Nvidia device pluin."
        )
            sys.exit(1)
        logging.info("Prerequisites- Nvidia device plugin present")
    except RuntimeError as e:
        logging.warning("An error occurred while checking Nvidia device plugin: %s",
        e
        )
        sys.exit(1)

def is_valid_ip(ip):
    """
    Validates if the provided string is a valid IP address.
    Args:
        ip (str): The IP address to validate.
    Returns:
        bool: True if the IP address is valid, False otherwise.
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def check_existing_deployment(service_name):
    """
    Checks if the pretrained model service is already deployed.
    Args:
        service_name (str): The name of the pretrained model service to check.
    Returns:
        bool: True if the service already exists, False otherwise.
    """
    try:
        existing_service = run_command(f"kubectl get svc {service_name}")
        if existing_service:
            logging.warning(
                "Service '%s' already exists. Skipping deployment.",
                service_name
            )
            return True
    except RuntimeError as e:
        if "NotFound" in str(e):
            logging.info(
                "Service '%s' is not present. Proceeding with deployment.",
                service_name
                )
        else:
            logging.error(
                "Failed to check service '%s': %s",
                service_name, e
                )
            raise
        return False
    return False

def deploy_pretrained_model(service_name):
    """
    Deploys the pretrained model using the defined YAML config.
    Args:
        service_name (str): The name of the service to deploy.
    """
    if not check_existing_deployment(service_name):
        logging.info("Creating pretrained model deployment...")
        run_command("kubectl apply -f -", input_data=PRETRAINED_MODEL_CONFIG)
        logging.info("""Deployment initiated. Check deployment status using kubectl get pods
        and kubectl get svc pretrained-model-service for external IP""")

def delete_pretrained_model_resources():
    """
    Deletes the pretrained model resources defined in the YAML config.
    This function deletes both the deployment and service for the pretrained model.
    If the resources are not found, it informs the user and does not raise an error.
    """
    logging.info("Deleting pretrained model deployment and service...")
    try:
        run_command("kubectl delete -f -", input_data=PRETRAINED_MODEL_CONFIG)
        logging.info("Pretrained model deployment and service deleted.")
    except RuntimeError as e:
        if "NotFound" in str(e):
            logging.warning(
                "Pretrained model deployment or service not found." 
                "They may have already been deleted."
            )
        elif K8S_EXCEPTION in str(e):
            logging.warning(
                "k8s, kubectl is not available or not configured properly"
            )
            sys.exit(1)
        else:
            logging.error("Failed to delete pretrained model resources: %s", e)
            raise

def get_pretrained_model_service_ip(svc_name):
    """
    Waits for the pretrained service to get an external IP and returns it.
    Args:
        service_name (str): The name of the pretrained model service to check.
    Returns:
        str: The external IP of the service, or None if the service does not exist.
    """
    max_retries = 5
    retry_count = 0
    while retry_count < max_retries:
        try:
            svc_ip = run_command(
                f"kubectl get svc {svc_name} -o jsonpath='{{.status.loadBalancer.ingress[0].ip}}'"
            )
            if svc_ip:
                return svc_ip
        except RuntimeError as e:
            if "NotFound" in str(e):
                logging.warning(
                    "Service '%s' not found. It may not be deployed yet. "
                    "To deploy it use --deploy tag",
                    svc_name
                )
            elif K8S_EXCEPTION in str(e):
                logging.warning(
                    "Kubectl is not found, and not able to locate service."
                    "Try inferencing by giving --service-ip"
                )
            return None
        retry_count += 1
        logging.info("Pretrained Model Service is not yet available. Retrying in 10 seconds...")
        time.sleep(10)
    logging.error(
        "Failed to get the external IP of the service '%s' after %d retries.",
        svc_name,
        max_retries
        )
    return None

def run_inferencing(service_ip, query):
    """
    Runs the inferencing process against the model using the provided query.

    Args:
        service_ip (str): The external IP of the pretrained model service.
        query (str): The query string to be sent to the model for inferencing.
    """
    url = f"http://{service_ip}:80/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    data = {"model": "pretrained_model", "messages": [{"role": "user", "content": query}]}
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        try:
            response_data = response.json()
            logging.info("Inference response received.")
        except ValueError:
            logging.error("Failed to decode JSON response from the service.")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        logging.error(
            "Failed to connect to service at IP: %s. The service may be starting or not running."
            "Try again after verifying service is running",
            service_ip
            )
        sys.exit(1)
    except requests.exceptions.Timeout:
        logging.error("The request to the service timed out.")
        sys.exit(1)
    except requests.exceptions.HTTPError as http_err:
        logging.error("HTTP error occurred: %s", http_err)
        sys.exit(1)
    except requests.exceptions.RequestException as req_err:
        logging.error("Inferencing failed due to an unexpected error: %s", req_err)
        sys.exit(1)

    if response_data.get('choices'):
        message = response_data['choices'][0]['message']['content']
        logging.info(message)
    else:
        logging.error("No valid response received from the pretrained model.")
        sys.exit(1)

def main():
    """
    Main function to handle argument parsing and orchestrate the deployment, 
    inferencing, and deletion. This function processes command-line arguments 
    for deploying the model, running inferencing, or deleting the Kubernetes resources.
    """
    parser = argparse.ArgumentParser(
      description="""Automated Dell Enterprise Pretrained Model Deployment and Inferencing.
      Prerequisites:
        - Kubernetes (k8s) must be installed and configured on your cluster.
        - Nvidia GPU should present in kube node and cuda must be installed.
        - Verify PRETRAINED_MODEL_CONFIG section for any changes and update user_HF_token if required by model. 
        - The Kube control plane needs an active Internet connection. If there is no active Internet connection, 
          you need to set the proxy environment variables to have access to the Internet. The proxy environment variables 
          should be set to the IP address of the control plane.  For example: 
          export http_proxy=http://<control_plane_ip>:3128 
          export https_proxy=http://<control_plane_ip>:3128 
        """,
        formatter_class=argparse.RawTextHelpFormatter
      )
    parser.add_argument(
      '--deploy',
      action='store_true',
      help="Deploy the Dell Enterprise Pretrained Model for Nvidia Platforms."
      )
    parser.add_argument(
      '--infer',
      nargs='?',
      const="What is Dell Technologies World?",
      help="Run the inferencing. Optionally pass query string."
      )
    parser.add_argument(
    '--service-ip',
    help="""Optional: Specify the External Load Balancer IP assigned to pretrained service
    for inferencing."""
    )
    parser.add_argument(
      '--delete',
      action='store_true',
      help="Delete the pretrained model Kubernetes resources."
      )
    args = parser.parse_args()
    if args.deploy:
        check_kubectl_availability() # Pre-requisite check
        check_nvidia_device_plugin_availability() # Pre-requisite check
        deploy_pretrained_model(SERVICE_NAME)
    elif args.infer:
        # Check if service IP is provided as an argument
        if args.service_ip:
            if is_valid_ip(args.service_ip):
                service_ip = args.service_ip
            else:
                logging.error("Invalid IP address format: %s", args.service_ip)
                sys.exit(1)
        else:
            # If no service IP is provided, retrieve it using the service name
            service_ip = get_pretrained_model_service_ip(SERVICE_NAME)
        if service_ip:
            run_inferencing(service_ip, args.infer)
    elif args.delete:
        delete_pretrained_model_resources()

if __name__ == "__main__":
    main()
