# Repo Manager samples

This directory contains concise Repo Manager input and output examples. The
[input contract](../docs/contracts/input-contract.md) and
[output contract](../docs/contracts/output-contract.md) are authoritative.

## Sample files

| File | Purpose |
|------|---------|
| `catalog_generator_input.txt` | Example input for catalog generation |
| `repo_manager_config.yml.sample` | Current repository policy and version/architecture layout |
| `repo_manager_endpoint_config.yml.sample` | Pulp HTTPS endpoint configuration |
| `repo_status.yml` | Illustrative status output produced after synchronization |

## Use the configuration samples

From `src/repo_manager`, copy the required sample into the active project:

```bash
cp samples/repo_manager_config.yml.sample \
  /opt/omnia/repo_manager/input/project_default/repo_manager_config.yml
```

Edit the copy for the catalog-selected versions, architectures and repository
sources. Then validate it from `src/repo_manager/playbooks`:

```bash
ansible-playbook validate/validate_config.yml
```

The catalog determines the active OS versions and architectures. The repository
configuration supplies global policy, optional registries, and repository
settings under `repositories.<version>.<architecture>.<repository>`.

`repo_status.yml` is a reference output, not an input file. At runtime Repo
Manager writes it to
`<REPO_MANAGER_DATA_PATH>/output/<project>/repo_status.yml`.

Do not place passwords, tokens, private keys or deployment-specific addresses
in committed samples.
