# Tools for Omnia

## change_personality
```
change_personality k|s <node_list>
```
Change the personality of a node (or list of nodes) to Kubernetes (`k`) or Slurm (`s`). System does not wait for currently running jobs to complete before making nodes available to the new personality.
