#!/bin/bash
set -uo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_manager_dir=$(cd "${script_dir}/.." && pwd)
repository_root=$(cd "${repo_manager_dir}/../.." && pwd)
readonly script_dir repo_manager_dir repository_root

validation_failed=0

echo "=========================================="
echo "Repo Manager Code Validation Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Run every validation from the Repo Manager domain root.
cd "${repo_manager_dir}" || exit 1

echo "Step 1: Running Ansible Lint..."
echo "----------------------------------------"
if ANSIBLE_CONFIG="${repo_manager_dir}/ansible.cfg" \
    ansible-lint \
    --config-file "${repository_root}/.config/ansible-lint.yml" \
    --format=pep8 . 2>&1; then
    echo -e "${GREEN}✓ Ansible-lint passed${NC}"
else
    echo -e "${RED}✗ Ansible-lint failed${NC}"
    validation_failed=1
fi
echo ""

echo "Step 2: Running Bandit Security Scan..."
echo "----------------------------------------"
if python3 -m bandit -r plugins/ -f screen -ll -ii 2>&1; then
    echo -e "${GREEN}✓ Bandit security scan passed${NC}"
else
    echo -e "${RED}✗ Bandit security scan failed${NC}"
    validation_failed=1
fi
echo ""

echo "Step 3: Python Syntax Check..."
echo "----------------------------------------"
if python3 -m compileall -q plugins/ 2>&1; then
    echo -e "${GREEN}✓ Python syntax check passed${NC}"
else
    echo -e "${RED}✗ Python syntax check failed${NC}"
    validation_failed=1
fi
echo ""

echo "Step 4: YAML Syntax Check..."
echo "----------------------------------------"
yaml_count=0
yaml_valid=true
while IFS= read -r -d '' file; do
    yaml_count=$((yaml_count + 1))
    if ! python3 -c \
        'import pathlib, sys, yaml; yaml.safe_load(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))' \
        "$file" 2>/dev/null; then
        echo "Invalid YAML: $file"
        yaml_valid=false
    fi
done < <(find . -type f \( -name '*.yml' -o -name '*.yaml' \) -print0)

if [ "$yaml_count" -eq 0 ]; then
    echo -e "${GREEN}✓ No YAML files to check${NC}"
elif [ "$yaml_valid" = true ]; then
    echo -e "${GREEN}✓ YAML syntax check passed (${yaml_count} files)${NC}"
else
    echo -e "${RED}✗ YAML syntax check failed${NC}"
    validation_failed=1
fi
echo ""

echo "=========================================="
if [ "$validation_failed" -ne 0 ]; then
    echo -e "${RED}Repo Manager validation failed.${NC}"
    echo "=========================================="
    exit 1
fi

echo -e "${GREEN}All validations passed!${NC}"
echo "=========================================="
