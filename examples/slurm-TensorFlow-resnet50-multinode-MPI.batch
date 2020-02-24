#!/bin/bash

#SBATCH -n 2
#SBATCH -N 2
#SBATCH -J TF-resnet50
#SBATCH -o %J-tf-resnet50.txt
#SBATCH -t 00:30:00


mpirun  \ 
      --map-by numa  \
      python  \
      /foo/tensorflow/benchmarks/scripts/tf_cnn_benchmarks/tf_cnn_benchmarks.py  \
      --batch_size=512  \
      --model=resnet50  \
      --variable_update=horovod  \
      --optimizer=momentum  \
      --nodistortions  \
      --gradient_repacking=8  \
      --weight_decay=1e-4  \
      --use_fp16=true  \
      --data_dir=/data/tensorflow/  \
      --data_name=imagenet
