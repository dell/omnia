#!/bin/bash
# =============================================================================
# PR4 Validation Tests — Monorepo Path Fixes, --build Option, Dockerfile
# =============================================================================
# Usage:  bash test/test_pr4_validation.sh
# Run from the repository root (omnia-bsm/).
#
# These tests validate:
#   1. omnia.sh --build option and help text
#   2. Container-repo path references in omnia.sh
#   3. Dockerfile sparse checkout configuration
#   4. GitLab role examples/ path resolution
#   5. BuildStream source path and rsync path
#   6. ansible.cfg relative path resolution
#   7. upgrade_checkup.yml path reference
#   8. build_images.sh and ContainerFile presence
# =============================================================================

# ── Color codes ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[34m'
NC='\033[0m'

PASS=0
FAIL=0
SKIP=0

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Test helpers ──
assert_pass() {
    local test_name="$1"
    PASS=$((PASS + 1))
    echo -e "  ${GREEN}✓ PASS${NC}: $test_name"
}

assert_fail() {
    local test_name="$1"
    local detail="$2"
    FAIL=$((FAIL + 1))
    echo -e "  ${RED}✗ FAIL${NC}: $test_name"
    [ -n "$detail" ] && echo -e "         ${YELLOW}$detail${NC}"
}

assert_skip() {
    local test_name="$1"
    local reason="$2"
    SKIP=$((SKIP + 1))
    echo -e "  ${YELLOW}⊘ SKIP${NC}: $test_name — $reason"
}

file_contains() {
    local file="$1"
    local pattern="$2"
    grep -q "$pattern" "$file" 2>/dev/null
}

file_not_contains() {
    local file="$1"
    local pattern="$2"
    ! grep -q "$pattern" "$file" 2>/dev/null
}

# =============================================================================
echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  PR4 Validation Tests — Monorepo Build & Path Fixes${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"

# =============================================================================
# TEST GROUP 1: omnia.sh --build option
# =============================================================================
echo -e "${BLUE}── 1. omnia.sh --build option ──${NC}"

OMNIA_SH="$REPO_ROOT/src/main/omnia.sh"

if [ ! -f "$OMNIA_SH" ]; then
    assert_fail "omnia.sh exists" "File not found: $OMNIA_SH"
else
    # 1.1 Help text includes --build
    if file_contains "$OMNIA_SH" "\-\-build"; then
        assert_pass "omnia.sh help includes --build option"
    else
        assert_fail "omnia.sh help includes --build option"
    fi

    # 1.2 Help text includes -b short option
    if file_contains "$OMNIA_SH" "\-b,.*\-\-build"; then
        assert_pass "omnia.sh help includes -b short option"
    else
        assert_fail "omnia.sh help includes -b short option"
    fi

    # 1.3 build_omnia_core_image function exists
    if file_contains "$OMNIA_SH" "build_omnia_core_image()"; then
        assert_pass "build_omnia_core_image() function defined"
    else
        assert_fail "build_omnia_core_image() function defined"
    fi

    # 1.4 --build case exists in main()
    if file_contains "$OMNIA_SH" "\-\-build|\-b)"; then
        assert_pass "--build|-b case exists in main()"
    else
        assert_fail "--build|-b case exists in main()"
    fi

    # 1.5 build function references build_images.sh via relative path
    if file_contains "$OMNIA_SH" "containers/build_images.sh"; then
        assert_pass "build function references containers/build_images.sh"
    else
        assert_fail "build function references containers/build_images.sh"
    fi

    # 1.6 main receives single arg
    if file_contains "$OMNIA_SH" 'main "$1"'; then
        assert_pass "main() receives single arg via \$1"
    else
        assert_fail "main() receives single arg via \$1"
    fi

    # 1.7 No omnia-artifactory references in omnia.sh
    if file_not_contains "$OMNIA_SH" "omnia-artifactory"; then
        assert_pass "No omnia-artifactory references in omnia.sh"
    else
        assert_fail "omnia.sh still contains omnia-artifactory references"
    fi

    # 1.8 validate_container_image uses --build
    if file_contains "$OMNIA_SH" "omnia.sh --build"; then
        assert_pass "validate_container_image directs user to ./omnia.sh --build"
    else
        assert_fail "validate_container_image should direct user to ./omnia.sh --build"
    fi

    # 1.9 omnia.sh lives under src/main/
    if [ -f "$REPO_ROOT/src/main/omnia.sh" ]; then
        assert_pass "omnia.sh located at src/main/omnia.sh"
    else
        assert_fail "omnia.sh should be at src/main/omnia.sh"
    fi

    # 1.10 No omnia.sh at repo root
    if [ ! -f "$REPO_ROOT/omnia.sh" ]; then
        assert_pass "No omnia.sh at repo root (moved to src/main/)"
    else
        assert_fail "omnia.sh should not exist at repo root"
    fi
fi

# =============================================================================
# TEST GROUP 2: Container-repo path references in omnia.sh
# =============================================================================
echo -e "\n${BLUE}── 2. Container-repo paths in omnia.sh ──${NC}"

if [ -f "$OMNIA_SH" ]; then
    # 2.1 Upgrade playbook paths use /omnia/src/playbooks/
    if file_contains "$OMNIA_SH" "/omnia/src/playbooks/upgrade/prepare_upgrade.yml"; then
        assert_pass "prepare_upgrade.yml path: /omnia/src/playbooks/upgrade/"
    else
        assert_fail "prepare_upgrade.yml path should be /omnia/src/playbooks/upgrade/"
    fi

    if file_contains "$OMNIA_SH" "/omnia/src/playbooks/upgrade/upgrade.yml"; then
        assert_pass "upgrade.yml path: /omnia/src/playbooks/upgrade/"
    else
        assert_fail "upgrade.yml path should be /omnia/src/playbooks/upgrade/"
    fi

    # 2.2 oim_cleanup path uses /omnia/src/playbooks/utils/
    if file_contains "$OMNIA_SH" "/omnia/src/playbooks/utils/oim_cleanup.yml"; then
        assert_pass "oim_cleanup.yml path: /omnia/src/playbooks/utils/"
    else
        assert_fail "oim_cleanup.yml path should be /omnia/src/playbooks/utils/"
    fi

    # 2.3 No stale /omnia/upgrade/ paths (without src/playbooks)
    stale_upgrade=$(grep -n '/omnia/upgrade/' "$OMNIA_SH" | grep -v '/omnia/src/' | grep -v '^#' || true)
    if [ -z "$stale_upgrade" ]; then
        assert_pass "No stale /omnia/upgrade/ paths (all use /omnia/src/playbooks/)"
    else
        assert_fail "Stale /omnia/upgrade/ paths found" "$stale_upgrade"
    fi

    # 2.4 No stale /omnia/utils/ paths
    stale_utils=$(grep -n '/omnia/utils/' "$OMNIA_SH" | grep -v '/omnia/src/' | grep -v '^#' || true)
    if [ -z "$stale_utils" ]; then
        assert_pass "No stale /omnia/utils/ paths (all use /omnia/src/playbooks/)"
    else
        assert_fail "Stale /omnia/utils/ paths found" "$stale_utils"
    fi

    # 2.5 No stale /omnia/oim_cleanup.yml
    if file_not_contains "$OMNIA_SH" "/omnia/oim_cleanup.yml"; then
        assert_pass "No stale /omnia/oim_cleanup.yml reference"
    else
        assert_fail "Stale /omnia/oim_cleanup.yml reference found"
    fi

    # 2.6 No rm -rf /omnia/omnia.sh (file won't exist with sparse checkout)
    if file_not_contains "$OMNIA_SH" 'rm.*-rf.*/omnia/omnia\.sh'; then
        assert_pass "No rm -rf /omnia/omnia.sh (sparse checkout, file absent)"
    else
        assert_fail "rm -rf /omnia/omnia.sh still present — remove it"
    fi

    # 2.7 Input copy uses /omnia/src/input/
    if file_contains "$OMNIA_SH" "/omnia/src/input"; then
        assert_pass "Input copy uses /omnia/src/input/"
    else
        assert_fail "Input copy should reference /omnia/src/input/"
    fi
fi

# =============================================================================
# TEST GROUP 3: Dockerfile sparse checkout
# =============================================================================
echo -e "\n${BLUE}── 3. Dockerfile configuration ──${NC}"

DOCKERFILE="$REPO_ROOT/src/containers/omnia_core/Dockerfile"

if [ ! -f "$DOCKERFILE" ]; then
    assert_fail "Dockerfile exists" "Not found: $DOCKERFILE"
else
    # 3.1 Uses COPY src/ instead of git clone
    if file_contains "$DOCKERFILE" "COPY src/ /omnia/src/"; then
        assert_pass "Dockerfile uses COPY src/ /omnia/src/"
    else
        assert_fail "Dockerfile should use COPY src/ /omnia/src/"
    fi

    # 3.2 No git clone present
    if file_not_contains "$DOCKERFILE" "git clone.*dell/omnia"; then
        assert_pass "No git clone in Dockerfile"
    else
        assert_fail "Dockerfile should not contain git clone"
    fi

    # 3.3 No OMNIA_VERSION build arg
    if file_not_contains "$DOCKERFILE" "ARG OMNIA_VERSION"; then
        assert_pass "No ARG OMNIA_VERSION (no git clone needed)"
    else
        assert_fail "ARG OMNIA_VERSION should be removed"
    fi

    # 3.4 WORKDIR is /omnia/src
    if file_contains "$DOCKERFILE" "WORKDIR /omnia/src"; then
        assert_pass "WORKDIR set to /omnia/src"
    else
        assert_fail "WORKDIR should be /omnia/src"
    fi

    # 3.5 bashrc cd target is /omnia/src
    if file_contains "$DOCKERFILE" 'cd /omnia/src'; then
        assert_pass "bashrc cd target is /omnia/src"
    else
        assert_fail "bashrc cd target should be /omnia/src"
    fi

    # 3.6 COPY paths use repo-root context (src/containers/omnia_core/)
    if file_contains "$DOCKERFILE" "COPY src/containers/omnia_core/entrypoint.sh"; then
        assert_pass "entrypoint.sh COPY uses repo-root context path"
    else
        assert_fail "entrypoint.sh COPY should use src/containers/omnia_core/ prefix"
    fi

    if file_contains "$DOCKERFILE" "COPY src/containers/omnia_core/cert-copy.sh"; then
        assert_pass "cert-copy.sh COPY uses repo-root context path"
    else
        assert_fail "cert-copy.sh COPY should use src/containers/omnia_core/ prefix"
    fi

    if file_contains "$DOCKERFILE" "COPY src/containers/omnia_core/pyproject.toml"; then
        assert_pass "pyproject.toml COPY uses repo-root context path"
    else
        assert_fail "pyproject.toml COPY should use src/containers/omnia_core/ prefix"
    fi
fi

# =============================================================================
# TEST GROUP 4: GitLab role examples/ path
# =============================================================================
echo -e "\n${BLUE}── 4. GitLab role examples/ paths ──${NC}"

GITLAB_VARS="$REPO_ROOT/src/playbooks/gitlab/roles/hosted_gitlab/vars/main.yml"
GITLAB_PUSH="$REPO_ROOT/src/playbooks/gitlab/roles/hosted_gitlab/tasks/push_example_catalogs.yml"

if [ -f "$GITLAB_VARS" ]; then
    # 4.1 role_path goes up 4 levels to reach src/
    if file_contains "$GITLAB_VARS" "role_path }}/../../../../examples/catalog"; then
        assert_pass "gitlab vars: role_path/../../../../examples/ (4 levels up)"
    else
        assert_fail "gitlab vars: should be role_path/../../../../examples/ (4 levels up)"
    fi
else
    assert_skip "gitlab vars/main.yml" "File not found"
fi

if [ -f "$GITLAB_PUSH" ]; then
    # 4.2 playbook_dir goes up 2 levels to reach src/
    if file_contains "$GITLAB_PUSH" "playbook_dir }}/../../examples/catalog"; then
        assert_pass "push_example_catalogs: playbook_dir/../../examples/ (2 levels up)"
    else
        assert_fail "push_example_catalogs: should be playbook_dir/../../examples/ (2 levels up)"
    fi
else
    assert_skip "push_example_catalogs.yml" "File not found"
fi

# 4.3 Verify examples/catalog/ directory exists at src/examples/catalog/
if [ -d "$REPO_ROOT/src/examples/catalog" ]; then
    assert_pass "src/examples/catalog/ directory exists"
else
    assert_fail "src/examples/catalog/ directory missing"
fi

# =============================================================================
# TEST GROUP 5: BuildStream paths
# =============================================================================
echo -e "\n${BLUE}── 5. BuildStream flow paths ──${NC}"

BS_VARS="$REPO_ROOT/src/playbooks/prepare_oim/roles/deploy_containers/build_stream/vars/main.yml"

if [ -f "$BS_VARS" ]; then
    # 5.1 Container-repo source path
    if file_contains "$BS_VARS" 'build_stream_source_path:.*"/omnia/src/build_stream"'; then
        assert_pass "build_stream_source_path: /omnia/src/build_stream"
    else
        assert_fail "build_stream_source_path should be /omnia/src/build_stream"
    fi

    # 5.2 rsync source uses 5 levels up from role
    if file_contains "$BS_VARS" "role_path }}/../../../../../build_stream/"; then
        assert_pass "bs_rsync_source: 5 levels up to src/build_stream/"
    else
        assert_fail "bs_rsync_source should be 5 levels up (/../../../../../build_stream/)"
    fi
else
    assert_skip "build_stream vars/main.yml" "File not found"
fi

# 5.3 Verify src/build_stream/ directory exists
if [ -d "$REPO_ROOT/src/build_stream" ]; then
    assert_pass "src/build_stream/ directory exists"
else
    assert_fail "src/build_stream/ directory missing"
fi

# 5.4 upgrade_build_stream example_catalog_path
UPGRADE_BS="$REPO_ROOT/src/playbooks/upgrade/playbooks/upgrade_build_stream.yml"
if [ -f "$UPGRADE_BS" ]; then
    if file_contains "$UPGRADE_BS" "playbook_dir }}/../../../examples/catalog"; then
        assert_pass "upgrade_build_stream: example_catalog_path 3 levels up"
    else
        assert_fail "upgrade_build_stream: example_catalog_path should be 3 levels up"
    fi
else
    assert_skip "upgrade_build_stream.yml" "File not found"
fi

# =============================================================================
# TEST GROUP 6: ansible.cfg relative paths
# =============================================================================
echo -e "\n${BLUE}── 6. ansible.cfg relative path resolution ──${NC}"

PLAYBOOKS_DIR="$REPO_ROOT/src/playbooks"
COMMON_DIR="$REPO_ROOT/src/common"

# Verify common/ directory exists
if [ -d "$COMMON_DIR" ]; then
    assert_pass "src/common/ directory exists"
else
    assert_fail "src/common/ directory missing"
fi

# Check each ansible.cfg references ../../common/ and the target exists
cfg_ok=true
for cfg in "$PLAYBOOKS_DIR"/*/ansible.cfg; do
    [ ! -f "$cfg" ] && continue
    subdir=$(dirname "$cfg")
    target="$subdir/../../common/callback_plugins"
    resolved=$(cd "$subdir" && cd ../../common/callback_plugins 2>/dev/null && pwd)
    if [ -z "$resolved" ]; then
        assert_fail "ansible.cfg path resolves: $(basename "$subdir")/ansible.cfg -> ../../common/callback_plugins"
        cfg_ok=false
    fi
done
if $cfg_ok; then
    assert_pass "All ansible.cfg ../../common/callback_plugins paths resolve correctly"
fi

# =============================================================================
# TEST GROUP 7: upgrade_checkup.yml
# =============================================================================
echo -e "\n${BLUE}── 7. upgrade_checkup.yml path reference ──${NC}"

UPGRADE_CHECK="$REPO_ROOT/src/playbooks/utils/upgrade_checkup.yml"

if [ -f "$UPGRADE_CHECK" ]; then
    if file_contains "$UPGRADE_CHECK" "/omnia/src/playbooks/upgrade/upgrade.yml"; then
        assert_pass "upgrade_checkup.yml: path uses /omnia/src/playbooks/"
    else
        assert_fail "upgrade_checkup.yml: should reference /omnia/src/playbooks/upgrade/upgrade.yml"
    fi
else
    assert_skip "upgrade_checkup.yml" "File not found"
fi

# =============================================================================
# TEST GROUP 8: Container build files
# =============================================================================
echo -e "\n${BLUE}── 8. Container build files ──${NC}"

CONTAINERS_DIR="$REPO_ROOT/src/containers"

# 8.1 build_images.sh exists
if [ -f "$CONTAINERS_DIR/build_images.sh" ]; then
    assert_pass "src/containers/build_images.sh exists"
else
    assert_fail "src/containers/build_images.sh missing"
fi

# 8.2 omnia_core/Dockerfile exists
if [ -f "$CONTAINERS_DIR/omnia_core/Dockerfile" ]; then
    assert_pass "src/containers/omnia_core/Dockerfile exists"
else
    assert_fail "src/containers/omnia_core/Dockerfile missing"
fi

# 8.3 build_images.sh uses REPO_ROOT as build context
if [ -f "$CONTAINERS_DIR/build_images.sh" ]; then
    if file_contains "$CONTAINERS_DIR/build_images.sh" 'OMNIA_CORE_DIR="${REPO_ROOT}"'; then
        assert_pass "build_images.sh: OMNIA_CORE_DIR uses REPO_ROOT"
    else
        assert_fail "build_images.sh: OMNIA_CORE_DIR should use REPO_ROOT"
    fi

    if file_contains "$CONTAINERS_DIR/build_images.sh" 'OMNIA_CORE_DOCKERFILE="src/containers/omnia_core/Dockerfile"'; then
        assert_pass "build_images.sh: Dockerfile path uses src/containers/omnia_core/"
    else
        assert_fail "build_images.sh: OMNIA_CORE_DOCKERFILE should point to src/containers/omnia_core/Dockerfile"
    fi

    # 8.4 No --build-arg OMNIA_VERSION in build commands
    if file_not_contains "$CONTAINERS_DIR/build_images.sh" 'build-arg OMNIA_VERSION'; then
        assert_pass "build_images.sh: No --build-arg OMNIA_VERSION"
    else
        assert_fail "build_images.sh: Should not pass --build-arg OMNIA_VERSION"
    fi

    # 8.5 No omnia-artifactory download instructions in build_images.sh
    if file_not_contains "$CONTAINERS_DIR/build_images.sh" "omnia-artifactory"; then
        assert_pass "build_images.sh: No omnia-artifactory references"
    else
        assert_fail "build_images.sh: Should not reference omnia-artifactory"
    fi
fi

# 8.5 Supporting files exist
for f in cert-copy.sh entrypoint.sh pyproject.toml uv.lock; do
    if [ -f "$CONTAINERS_DIR/omnia_core/$f" ]; then
        assert_pass "omnia_core/$f exists"
    else
        assert_fail "omnia_core/$f missing"
    fi
done

# =============================================================================
# TEST GROUP 9: Directory structure validation
# =============================================================================
echo -e "\n${BLUE}── 9. Monorepo directory structure ──${NC}"

expected_dirs=(
    "src/playbooks/upgrade"
    "src/playbooks/rollback"
    "src/playbooks/utils"
    "src/playbooks/provision"
    "src/playbooks/discovery"
    "src/playbooks/telemetry"
    "src/playbooks/local_repo"
    "src/playbooks/prepare_oim"
    "src/playbooks/gitlab"
    "src/playbooks/input_validation"
    "src/playbooks/build_image_x86_64"
    "src/playbooks/build_image_aarch64"
    "src/playbooks/log_collector"
    "src/common"
    "src/input"
    "src/examples"
    "src/build_stream"
    "src/main"
    "src/containers/omnia_core"
)

for d in "${expected_dirs[@]}"; do
    if [ -d "$REPO_ROOT/$d" ]; then
        assert_pass "Directory exists: $d"
    else
        assert_fail "Directory missing: $d"
    fi
done

# =============================================================================
# SUMMARY
# =============================================================================
TOTAL=$((PASS + FAIL + SKIP))
echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  TEST SUMMARY${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "  Total:   ${TOTAL}"
echo -e "  ${GREEN}Passed:  ${PASS}${NC}"
echo -e "  ${RED}Failed:  ${FAIL}${NC}"
echo -e "  ${YELLOW}Skipped: ${SKIP}${NC}"
echo ""

if [ "$FAIL" -gt 0 ]; then
    echo -e "${RED}PR4 validation FAILED — fix the above issues before merging.${NC}"
    exit 1
else
    echo -e "${GREEN}PR4 validation PASSED — all checks OK.${NC}"
    exit 0
fi
