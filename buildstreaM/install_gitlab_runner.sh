#!/bin/bash
# install_gitlab_runner.sh
# Deploys GitLab Runner as a Podman container and registers it.
#
# Usage:
#   sudo ./install_gitlab_runner.sh              # interactive registration
#   sudo GITLAB_URL=http://host REGISTRATION_TOKEN=glrt-xxx ./install_gitlab_runner.sh --auto

set -euo pipefail

RUNNER_NAME="gitlab-runner"
# Use Docker Hub path explicitly; avoids RHEL registry auth prompts triggered by short-name resolution
RUNNER_IMAGE="docker.io/gitlab/gitlab-runner:latest"
RUNNER_CONFIG_DIR="/srv/gitlab-runner/config"
RUNNER_DESCRIPTION="${RUNNER_DESCRIPTION:-omnia-docker-runner}"
RUNNER_TAGS="${RUNNER_TAGS:-docker,linux}"
RUNNER_EXECUTOR="${RUNNER_EXECUTOR:-docker}"
DEFAULT_DOCKER_IMAGE="${DEFAULT_DOCKER_IMAGE:-alpine:latest}"
# Podman socket that exposes the Docker-compatible API; override if your distro uses a different path
PODMAN_SOCKET="${PODMAN_SOCKET:-/run/podman/podman.sock}"
CONTAINER_SOCKET_PATH="${CONTAINER_SOCKET_PATH:-/var/run/docker.sock}"

GITLAB_URL="${GITLAB_URL:-http://100.10.0.83}"
REGISTRATION_TOKEN="${REGISTRATION_TOKEN:-}"

log()   { echo -e "\e[32m[INFO]\e[0m  $*"; }
warn()  { echo -e "\e[33m[WARN]\e[0m  $*"; }
error() { echo -e "\e[31m[ERR]\e[0m   $*"; }

require_root() {
  if [[ $EUID -ne 0 ]]; then
    error "Run as root or use sudo"
    exit 1
  fi
}

check_podman() {
  if ! command -v podman &>/dev/null; then
    error "Podman not installed"
    exit 1
  fi
}

ensure_podman_socket() {
  if [[ -S "$PODMAN_SOCKET" ]]; then
    log "Podman API socket available at $PODMAN_SOCKET"
    return
  fi

  if command -v systemctl &>/dev/null; then
    warn "Podman socket not found at $PODMAN_SOCKET; attempting to enable podman.socket"
    systemctl enable --now podman.socket >/dev/null 2>&1 || true
  fi

  if [[ -S "$PODMAN_SOCKET" ]]; then
    log "Podman socket created via podman.socket service"
    return
  fi

  error "Podman API socket not found at $PODMAN_SOCKET. Set PODMAN_SOCKET env var or start podman.socket manually."
  exit 1
}

prepare_dir() {
  mkdir -p "$RUNNER_CONFIG_DIR"
  chmod 755 "$RUNNER_CONFIG_DIR"
  if command -v restorecon &>/dev/null; then
    restorecon -RF "$RUNNER_CONFIG_DIR" || true
  fi
}

remove_existing() {
  if podman ps -a --format '{{.Names}}' | grep -q "^${RUNNER_NAME}$"; then
    warn "Existing runner container found; removing"
    podman stop "$RUNNER_NAME" 2>/dev/null || true
    podman rm "$RUNNER_NAME" 2>/dev/null || true
  fi
}

run_container() {
  log "Starting GitLab Runner container"
  podman run -d \
    --name "$RUNNER_NAME" \
    --restart always \
    -v "$RUNNER_CONFIG_DIR:/etc/gitlab-runner:Z" \
    -v "$PODMAN_SOCKET:$CONTAINER_SOCKET_PATH:Z" \
    "$RUNNER_IMAGE"
}

register_runner_interactive() {
  podman exec -it "$RUNNER_NAME" gitlab-runner register
}

register_runner_auto() {
  if [[ -z "$REGISTRATION_TOKEN" ]]; then
    error "REGISTRATION_TOKEN env var required for --auto"
    exit 1
  fi
  podman exec "$RUNNER_NAME" gitlab-runner register \
    --non-interactive \
    --url "$GITLAB_URL" \
    --registration-token "$REGISTRATION_TOKEN" \
    --executor "$RUNNER_EXECUTOR" \
    --docker-image "$DEFAULT_DOCKER_IMAGE" \
    --description "$RUNNER_DESCRIPTION" \
    --tag-list "$RUNNER_TAGS" \
    --run-untagged=true \
    --locked=false
}

verify_runner() {
  podman exec "$RUNNER_NAME" gitlab-runner verify
  podman exec "$RUNNER_NAME" gitlab-runner list
}

main() {
  require_root
  check_podman
  ensure_podman_socket
  prepare_dir
  remove_existing
  run_container

  if [[ "${1:-}" == "--auto" ]]; then
    register_runner_auto
  else
    register_runner_interactive
  fi

  verify_runner
  log "Runner deployed. Check GitLab Settings → CI/CD → Runners."
}

main "$@"
