# Dataset: k8s_only

Kubernetes-only dataset for orchestrator K8s test automation.

---

## Profile

| Parameter | Value |
|-----------|-------|
| Profile | `k8s_only` |
| pxe_mapping_file_path | `` |
| language | `en_US.UTF-8` |
| dns_enabled | `False` |
| dcgm_enabled | `True` |

## Generated Files

```
k8s_only/
  input/network_spec.yml
  input/orchestrator_config.yml
  repo_manager_output/
```

## Regenerate

```bash
cd datasets/generator/
python generate_dataset.py k8s_only k8s_only --force
```
