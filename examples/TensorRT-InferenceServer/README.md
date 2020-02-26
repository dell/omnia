# Run Nvidia's TensorRT Inference Server

Clone the repo

`git clone https://github.com/NVIDIA/tensorrt-inference-server.git`

Download models

`cd tensorrt-inference-server/docs/examples/`
`./fetch_models.sh`

Copy models to shared NFS location

`cp -rp model_repository ensemble_model_repository /home/k8sSHARE`

## Deploy Prometheus and Grafana

Prometheus collects metrics for viewing in Grafana. Install the prometheus-operator for these components. The serviceMonitorSelectorNilUsesHelmValues flag is needed so that Prometheus can find the inference server metrics in the example release deployed below:

`helm install --name example-metrics --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false stable/prometheus-operator`

Setup port-forward to the Grafana service for local access

`kubectl port-forward service/example-metrics-grafana 8080:80`

Navigate in your browser to localhost:8080 for the Grafana login page. 
`username=admin password=prom-operator`

## Deploy TensorRT Inference Server
Change to helm chart directory
`cd ~/tensorrt-inference-server/deploy/single_server/`'

Modify `values.yaml` changing `modelRepositoryPath`

<pre>
image:
  imageName: nvcr.io/nvidia/tensorrtserver:20.01-py3
  pullPolicy: IfNotPresent
  #modelRepositoryPath: gs://tensorrt-inference-server-repository/model_repository
  modelRepositoryPath: /data/model_repository
  numGpus: 1
 </pre>

Modify `templates/deployment.yaml` in **bold** to add the local NFS mount:
<pre>
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ template "tensorrt-inference-server.fullname" . }}
  namespace: {{ .Release.Namespace }}
  labels:
    app: {{ template "tensorrt-inference-server.name" . }}
    chart: {{ template "tensorrt-inference-server.chart" . }}
    release: {{ .Release.Name }}
    heritage: {{ .Release.Service }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ template "tensorrt-inference-server.name" . }}
      release: {{ .Release.Name }}
  template:
    metadata:
      labels:
        app: {{ template "tensorrt-inference-server.name" . }}
        release: {{ .Release.Name }}

    spec:
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.imageName }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
         <b style='background-color:yellow'> volumeMounts:
            - mountPath: /data/
              name: work-volume</b>
          resources:
            limits:
              nvidia.com/gpu: {{ .Values.image.numGpus }}

          args: ["trtserver", "--model-store={{ .Values.image.modelRepositoryPath }}"]

          ports:
            - containerPort: 8000
              name: http
            - containerPort: 8001
              name: grpc
            - containerPort: 8002
              name: metrics
          livenessProbe:
            httpGet:
              path: /api/health/live
              port: http
          readinessProbe:
            initialDelaySeconds: 5
            periodSeconds: 5
            httpGet:
              path: /api/health/ready
              port: http

          securityContext:
            runAsUser: 1000
            fsGroup: 1000
   <b>   volumes:
      - name: work-volume
        hostPath:
          # directory locally mounted on host
          path: /home/k8sSHARE
          type: Directory
   </b>
   </pre>


### Deploy the inference server using the default configuration with:

<pre>
cd ~/tensorrt-inference-server/deploy/single_server/
$ helm install --name example .
</pre>

### Verify deployment
<pre>
helm ls
NAME           	REVISION	UPDATED                 	STATUS  	CHART                          	APP VERSION	NAMESPACE
example        	1       	Wed Feb 26 15:46:18 2020	DEPLOYED	tensorrt-inference-server-1.0.0	1.0        	default  
example-metrics	1       	Tue Feb 25 17:45:54 2020	DEPLOYED	prometheus-operator-8.9.2      	0.36.0     	default  
</pre>

<pre>
kubectl get pods
NAME                                                     READY   STATUS    RESTARTS   AGE
example-tensorrt-inference-server-f45d865dc-62c46        1/1     Running   0          53m
</pre>

<pre>
kubectl get svc
NAME                                        TYPE           CLUSTER-IP       EXTERNAL-IP      PORT(S)                                        AGE
...
example-tensorrt-inference-server           LoadBalancer   10.150.77.138    192.168.60.150   8000:31165/TCP,8001:31408/TCP,8002:30566/TCP   53m
</pre>

## Setup NGC login secret for nvcr.io

<pre> kubectl create secret docker-registry <your-secret-name> --docker-server=<your-registry-server> --docker-username=<your-registry-username> --docker-password=<your-registry-apikey> --docker-email=<your-email>
</pre> 

Parameter Description:
docker-registry <your-secret-name> – the name you will use for this secret
docker-server <your-registry-server> – nvcr.io is the container registry for NGC
docker-username <your-registry-username> – for nvcr.io this is ‘$oauthtoken’ (including quotes)
docker-password <your-registry-apikey> – this is the API Key you obtained earlier
docker-email <your-email> – your NGC email address

Example (you will need to generate your own oauth token)
`kubectl create secret docker-registry ngc-secret --docker-server=nvcr.io --docker-username='$oauthtoken' --docker-password=clkaw309f3jfaJ002EIVCJAC0Cpcklajser90wezxc98wdn09ICJA09xjc09j09JV00JV0JVCLR0WQE8ACZz --docker-email=john@example.com`

Verify your secret has been stored:
<pre>
kubectl get secrets
NAME                                                          TYPE                                  DATA   AGE
...
ngc-secret                                                    kubernetes.io/dockerconfigjson        1      106m
</pre>

## Run TensorRT Client
`kubectl apply -f trt-client.yaml`

Verify it is running:
<pre>
kubectl get pod tensorrt-client 
NAME              READY   STATUS    RESTARTS   AGE
tensorrt-client   1/1     Running   0          5m
</pre>

Run the inception test using the client Pod. The TensorRT Inference Service IP Address
<pre>
kubectl exec -it tensorrt-client -- /bin/bash -c "image_client -u 192.168.60.150:8000 -m resnet50_netdef -s INCEPTION images/mug.jpg"
Request 0, batch size 1
Image 'images/mug.jpg':
    504 (COFFEE MUG) = 0.723992
</pre>





