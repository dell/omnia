# MetalLB 

MetalLB is a load-balancer implementation for bare metal Kubernetes clusters, using standard routing protocols.
https://metallb.universe.tf/

Omnia installs MetalLB by manifest in the playbook `startservices`. A default configuration is provided for layer2 protocol and an example for providing an address pool. Modify metal-config.yaml to suit your network requirements and apply the changes using with: 

``` 
kubectl apply -f metal-config.yaml
```
