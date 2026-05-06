#!/usr/bin/env bash
#
# setup_local_model.sh
#
# Purpose:
#   Install and prepare a local coding model for AI Dev Squad on macOS.
#
# What this script does:
#   1. Verifies the OS and CPU architecture
#   2. Installs Ollama if it is missing
#   3. Starts Ollama if needed
#   4. Pulls the qwen2.5-coder:7b model
#   5. Runs a small API test against the local Ollama server
#   6. Prints the config values to use in AI Dev Squad
#
# Notes:
#   - Designed for macOS on Apple Silicon
#   - Safe to run multiple times
#   - Uses the official Ollama installer
#   - Exits on the first error
#

set -euo pipefail

# -----------------------------
# Config
# -----------------------------
MODEL_NAME="qwen2.5-coder:7b"
OLLAMA_API_URL="http://localhost:11434"
OLLAMA_CHAT_API="${OLLAMA_API_URL}/api/chat"
OLLAMA_TAGS_API="${OLLAMA_API_URL}/api/tags"
INSTALL_SCRIPT_URL="https://ollama.com/install.sh"

# -----------------------------
# Simple logging helpers
# -----------------------------
log() {
  printf "\n[AI Dev Squad] %s\n" "$1"
}

warn() {
  printf "\n[AI Dev Squad][WARN] %s\n" "$1"
}

fail() {
  printf "\n[AI Dev Squad][ERROR] %s\n" "$1" >&2
  exit 1
}

# -----------------------------
# Environment checks
# -----------------------------
check_macos() {
  log "Checking operating system..."

  if [[ "$(uname -s)" != "Darwin" ]]; then
    fail "This script is for macOS only."
  fi

  log "macOS detected."
}

check_architecture() {
  log "Checking CPU architecture..."

  local arch
  arch="$(uname -m)"

  if [[ "${arch}" != "arm64" ]]; then
    warn "This script was prepared for Apple Silicon. Current architecture: ${arch}"
  else
    log "Apple Silicon detected (${arch})."
  fi
}

check_required_commands() {
  log "Checking required base commands..."

  command -v curl >/dev/null 2>&1 || fail "curl is required but not installed."
  command -v bash >/dev/null 2>&1 || fail "bash is required but not installed."

  log "Base commands are available."
}

# -----------------------------
# Ollama install / startup
# -----------------------------
install_ollama_if_missing() {
  if command -v ollama >/dev/null 2>&1; then
    log "Ollama is already installed."
    return
  fi

  log "Ollama is not installed. Installing now..."
  log "Using official installer: ${INSTALL_SCRIPT_URL}"

  curl -fsSL "${INSTALL_SCRIPT_URL}" | sh

  if ! command -v ollama >/dev/null 2>&1; then
    fail "Ollama install finished, but the 'ollama' command is still not available on PATH."
  fi

  log "Ollama installation completed."
}

start_ollama_if_needed() {
  log "Checking whether Ollama server is reachable..."

  if curl -fsS "${OLLAMA_TAGS_API}" >/dev/null 2>&1; then
    log "Ollama API is already running."
    return
  fi

  log "Ollama API is not running. Trying to start Ollama..."

  # Try to open the macOS app first. This is the cleanest path on macOS.
  open -a Ollama >/dev/null 2>&1 || true

  wait_for_ollama
}

wait_for_ollama() {
  log "Waiting for Ollama to become ready..."

  local max_attempts=30
  local attempt=1

  while (( attempt <= max_attempts )); do
    if curl -fsS "${OLLAMA_TAGS_API}" >/dev/null 2>&1; then
      log "Ollama API is ready."
      return
    fi

    printf "[AI Dev Squad] Waiting... (%d/%d)\n" "${attempt}" "${max_attempts}"
    sleep 2
    attempt=$((attempt + 1))
  done

  fail "Ollama did not become ready in time. Try opening the Ollama app manually, then rerun this script."
}

# -----------------------------
# Model setup
# -----------------------------
pull_model() {
  log "Pulling model: ${MODEL_NAME}"
  ollama pull "${MODEL_NAME}"
  log "Model pull completed."
}

verify_model_present() {
  log "Verifying that the model is available locally..."

  if ! ollama list | grep -Fq "${MODEL_NAME}"; then
    fail "Model ${MODEL_NAME} was not found in 'ollama list' after pull."
  fi

  log "Model is available locally."
}

# -----------------------------
# API test
# -----------------------------
test_model_api() {
  log "Running a small local API test..."

  local response
  response="$(
    curl -fsS "${OLLAMA_CHAT_API}" \
      -H "Content-Type: application/json" \
      -d "{
        \"model\": \"${MODEL_NAME}\",
        \"messages\": [
          {
            \"role\": \"user\",
            \"content\": \"Reply with exactly one short line: local model ready\"
          }
        ],
        \"stream\": false
      }"
  )"

  printf "\n[AI Dev Squad] Test response:\n%s\n" "${response}"
  log "Local model API test completed."
}

# -----------------------------
# Final guidance
# -----------------------------
print_next_steps() {
  cat <<EOF

[AI Dev Squad] Setup completed successfully.

Use these values in your AI Dev Squad config:

DEFAULT_MODEL_PROVIDER=local
LOCAL_MODEL_NAME=${MODEL_NAME}

Local Ollama endpoint:
${OLLAMA_API_URL}

Quick manual tests:
  ollama run ${MODEL_NAME}
  curl ${OLLAMA_CHAT_API} \\
    -H "Content-Type: application/json" \\
    -d '{
      "model": "${MODEL_NAME}",
      "messages": [{"role": "user", "content": "Hello!"}],
      "stream": false
    }'

Recommended next implementation step:
- connect app/models/local_provider.py to Ollama on ${OLLAMA_API_URL}

EOF
}

# -----------------------------
# Main
# -----------------------------
main() {
  log "Starting local model setup for AI Dev Squad..."

  check_macos
  check_architecture
  check_required_commands
  install_ollama_if_missing
  start_ollama_if_needed
  pull_model
  verify_model_present
  test_model_api
  print_next_steps

  log "All done."
}

main "$@"