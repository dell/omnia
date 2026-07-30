# Telemetry Input Validation — L2 Enhancement

## Summary
Added L2 validation to verify that `cluster_mount` path exists on the `kube_vip` host.

## Implementation Details

### Files Modified
1. **`plugins/module_utils/input_validation/validation_flows/telemetry_validation.py`**
   - Added `subprocess` import for SSH execution
   - Enhanced `validate_telemetry_packages()` function with cross-file validation
   
2. **`plugins/module_utils/input_validation/common_utils/en_us_validation_msg.py`**
   - Added 3 new validation messages:
     - `CLUSTER_MOUNT_PATH_NOT_FOUND_ON_KUBE_VIP_MSG`
     - `CLUSTER_MOUNT_KUBE_VIP_NOT_FOUND_MSG`
     - `CLUSTER_MOUNT_SSH_CHECK_FAILED_MSG`

### Validation Logic Flow

When `telemetry_packages.yml` is validated:

1. **L1 (Schema)**: `cluster_mount` must be non-empty (existing check)
2. **L2 (Logic)**: New cross-file validation:
   - Load `telemetry_config.yml` from same directory
   - Extract `kube_vip` value
   - SSH to `kube_vip` host and run `test -d <cluster_mount>`
   - Fail if:
     - Path does not exist on remote host
     - SSH connection fails
     - `kube_vip` is not defined in `telemetry_config.yml`

### SSH Command Details
```bash
ssh -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    -o ConnectTimeout=10 \
    <kube_vip> \
    "test -d <cluster_mount>"
```

- **Timeout**: 15 seconds
- **Return code 0**: Path exists ✅
- **Return code != 0**: Path does not exist ❌

### Error Scenarios

| Scenario | Error Message |
|----------|---------------|
| Path does not exist on kube_vip | `CLUSTER_MOUNT_PATH_NOT_FOUND_ON_KUBE_VIP_MSG` |
| kube_vip not defined in telemetry_config.yml | `CLUSTER_MOUNT_KUBE_VIP_NOT_FOUND_MSG` |
| SSH connection/timeout failure | `CLUSTER_MOUNT_SSH_CHECK_FAILED_MSG` |

### Testing

To test this validation:

1. **Positive test** (should pass):
   ```bash
   # On kube_vip host, create the mount point
   ssh <kube_vip> "mkdir -p /opt/omnia/k8s_mount"
   
   # Set in telemetry_packages.yml
   cluster_mount: "/opt/omnia/k8s_mount"
   
   # Run validation
   ansible-playbook playbooks/validation.yml
   ```

2. **Negative test** (should fail):
   ```bash
   # Set non-existent path in telemetry_packages.yml
   cluster_mount: "/nonexistent/path"
   
   # Run validation — should fail with CLUSTER_MOUNT_PATH_NOT_FOUND_ON_KUBE_VIP_MSG
   ansible-playbook playbooks/validation.yml
   ```

### Dependencies
- SSH access from validation host to `kube_vip` (passwordless SSH keys)
- `telemetry_config.yml` must exist in same directory as `telemetry_packages.yml`
- `kube_vip` must be defined in `telemetry_config.yml`

### Graceful Degradation
- If `telemetry_config.yml` is missing or cannot be parsed, validation logs a warning and skips the remote path check
- If SSH fails (network/auth issues), validation fails with clear error message
