How to Run Nvidia's TensorRT Inference Server

Clone the repo

````git clone https://github.com/NVIDIA/tensorrt-inference-server.git````

Download models

````cd tensorrt-inference-server/docs/examples/````
````./fetch_models.sh````

Copy models to shared NFS location

````cp -rp model_repository ensemble_model_repository /home/k8sSHARE````

Deploy Prometheus and Grafana

Prometheus collects metrics for viewing in Grafana. Install the prometheus-operator for these components. The serviceMonitorSelectorNilUsesHelmValues flag is needed so that Prometheus can find the inference server metrics in the example release deployed below:

````helm install --name example-metrics --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false stable/prometheus-operator````

Setup port-forward to the Grafana service for local access:

````kubectl port-forward service/example-metrics-grafana 8080:80````

Navigate in your browser to localhost:8080 for the Grafana login page. 
````username=admin password=prom-operator```` 
