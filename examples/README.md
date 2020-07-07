# Examples


The examples [K8s Submit](https://github.com/dellhpc/omnia/blob/devel/examples/k8s-TensorFlow-resnet50-multinode-MPIOperator.yaml) and [SLURM submit](https://github.com/dellhpc/omnia/blob/devel/examples/slurm-TensorFlow-resnet50-multinode-MPI.batch) are provide as examples for running the resnet50 benchmark with TensorFlow on 8 GPUs using 2 C4140s.

## Submitting the example

# K8s
```` kubectl create -f k8s-TensorFlow-resnet50-multinode-MPIOperator.yaml ````

# Slurm
```` sbatch slurm-TensorFlow-resnet50-multinode-MPI.batch ````
