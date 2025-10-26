function _prometheus_send() {
  if [[ -z "$PROMETHEUS_ON" ]]; then return; fi
  local CMD="$1"
  local EC="$2"
  local CWD="$PWD"
  local TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local ID=$(uuidgen)
  /usr/bin/curl -sS -X POST http://localhost:6060/ingest/terminal \
    -H 'Content-Type: application/json' \
    -d "{\"id\":\"$ID\",\"ts\":\"$TS\",\"actor\":\"$USER\",\"payload\":{\"cwd\":\"$CWD\",\"cmd\":\"${CMD//\"/\\\"}\",\"exit_code\":$EC}}" >/dev/null || true
}

function preexec() { typeset -g __PROMETHEUS_LAST_CMD="$1"; }
function precmd() {
  local last_status=$?
  if [[ -n "$__PROMETHEUS_LAST_CMD" ]]; then
    _prometheus_send "$__PROMETHEUS_LAST_CMD" "$last_status"
    unset __PROMETHEUS_LAST_CMD
  fi
}
