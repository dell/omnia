> **_Update inventory.ini with appropriate host_**

**command to run the playbook:**

```
ansible-playbook -i inventory.yml k8s-upgrade.yml -e "k8s_upgrade_version=1.22.15"
```

> **_NOTE:_** Use **--tags manager or compute** to upgrade manager only or the compute only.

**avaliable options for k8s-versions:**

- "1.20.15"
- "1.21.14"
- "1.22.15"
- "1.23.17"
