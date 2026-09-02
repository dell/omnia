#!/bin/bash
set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_MANAGER_DIR=$(cd "${SCRIPT_DIR}/.." && pwd)
REPO_ROOT=$(cd "${REPO_MANAGER_DIR}/../.." && pwd)

export ANSIBLE_CONFIG="${REPO_MANAGER_DIR}/playbooks/ansible.cfg"

echo "=========================================="
echo "Repo Manager Code Validation Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to repo_manager directory
cd "${REPO_MANAGER_DIR}"

echo "Step 1: Running Ansible Lint..."
echo "----------------------------------------"
if ansible-lint \
    --config="${REPO_ROOT}/.config/ansible-lint.yml" \
    "${REPO_MANAGER_DIR}" \
    --force-color 2>&1; then
    echo -e "${GREEN}✓ Ansible-lint passed${NC}"
else
    echo -e "${RED}✗ Ansible-lint failed${NC}"
    exit 1
fi
echo ""

echo "Step 2: Running Bandit Security Scan..."
echo "----------------------------------------"
if python -m bandit -r plugins/ -f screen --severity-level medium 2>&1; then
    echo -e "${GREEN}✓ Bandit security scan passed${NC}"
else
    echo -e "${YELLOW}⚠ Bandit found issues (review output)${NC}"
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
yaml_files=$(find . -name '*.yml' -o -name '*.yaml' 2>/dev/null || true)
if [ -z "$yaml_files" ]; then
    echo -e "${GREEN}✓ No YAML files to check${NC}"
else
    valid=true
    for file in $yaml_files; do
        if python -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
            continue
        else
            echo "Invalid YAML: $file"
            valid=false
        fi
    done
    if [ "$valid" = true ]; then
        echo -e "${GREEN}✓ YAML syntax check passed${NC}"
    else
        echo -e "${RED}✗ YAML syntax check failed${NC}"
        exit 1
    fi
fi
echo ""

echo "=========================================="
echo -e "${GREEN}All validations completed!${NC}"
echo "=========================================="
