#!/bin/bash
set -euo pipefail

echo "=========================================="
echo "Repo Manager Code Validation Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Change to repo_manager directory
cd "$(dirname "$0")/.."
validation_tmp_dir=$(mktemp -d /tmp/repo-manager-validation.XXXXXX)
readonly validation_tmp_dir
trap 'rm -rf -- "$validation_tmp_dir"' EXIT
export PYTHONPYCACHEPREFIX="$validation_tmp_dir/pycache"

echo "Step 1: Running Ansible Lint..."
echo "----------------------------------------"
if ANSIBLE_CONFIG="$PWD/playbooks/ansible.cfg" ansible-lint --config ../../.config/ansible-lint.yml . --force-color 2>&1; then
    echo -e "${GREEN}✓ Ansible-lint passed${NC}"
else
    echo -e "${RED}✗ Ansible-lint failed${NC}"
    exit 1
fi
echo ""

echo "Step 2: Running Bandit Security Scan..."
echo "----------------------------------------"
if python -m bandit -r plugins/ -f screen -ll -ii 2>&1; then
    echo -e "${GREEN}✓ Bandit security scan passed${NC}"
else
    echo -e "${RED}✗ Bandit security scan failed${NC}"
    exit 1
fi
echo ""

echo "Step 3: Python Syntax Check..."
echo "----------------------------------------"
if find plugins/ -name "*.py" -exec python -m py_compile {} \; 2>&1; then
    echo -e "${GREEN}✓ Python syntax check passed${NC}"
else
    echo -e "${RED}✗ Python syntax check failed${NC}"
    exit 1
fi
echo ""

echo "Step 4: YAML Syntax Check..."
echo "----------------------------------------"
yaml_file_count=0
valid=true
while IFS= read -r -d '' file; do
    yaml_file_count=$((yaml_file_count + 1))
    if python -c 'import sys, yaml; yaml.safe_load(open(sys.argv[1], encoding="utf-8"))' "$file" 2>/dev/null; then
        continue
    fi
    echo "Invalid YAML: $file"
    valid=false
done < <(find . -type f \( -name '*.yml' -o -name '*.yaml' \) -print0)

if [ "$yaml_file_count" -eq 0 ]; then
    echo -e "${GREEN}✓ No YAML files to check${NC}"
elif [ "$valid" = true ]; then
    echo -e "${GREEN}✓ YAML syntax check passed${NC}"
else
    echo -e "${RED}✗ YAML syntax check failed${NC}"
    exit 1
fi
echo ""

echo "=========================================="
echo -e "${GREEN}All validations completed!${NC}"
echo "=========================================="
