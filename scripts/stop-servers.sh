#!/usr/bin/env bash
# Stop every UltraRAG MCP server, browser UI, gateway, and UltraRAG child that
# was started from a server in this collection.
#
#   scripts/stop-servers.sh                    stop everything it recognises
#   scripts/stop-servers.sh --dry-run          list what it would stop
#   scripts/stop-servers.sh --project PATH     only that project's process tree
#   scripts/stop-servers.sh --timeout SECONDS  wait before SIGKILL (default 10)
#
# Why this exists: a stdio MCP server belongs to the client that started it, so a
# client reload can leave a server behind, and each server owns a vanilla gateway
# and, through it, UltraRAG's corpus and retriever children. Every stdio child is
# also started in its own session, so a process-group kill from a launcher cannot
# reach it.
#
# This script identifies those processes by their own entry points, walks each
# family, and stops it by explicit PID: SIGTERM first, SIGKILL only for what
# ignores it. It never uses a pattern kill, which is the rule each server's own
# documentation states for stopping a running server.
set -uo pipefail

DRY_RUN=0
PROJECT=""
TIMEOUT=10

usage() {
  sed -n '2,18p' "$0" | sed -e 's/^# \{0,1\}//'
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --project)
      [ "$#" -ge 2 ] || { printf 'stop-servers.sh: --project needs a path\n' >&2; exit 2; }
      PROJECT="$2"; shift ;;
    --timeout)
      [ "$#" -ge 2 ] || { printf 'stop-servers.sh: --timeout needs a number\n' >&2; exit 2; }
      TIMEOUT="$2"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'stop-servers.sh: unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if [ -n "$PROJECT" ]; then
  PROJECT="$(cd -- "$PROJECT" 2>/dev/null && pwd -P)" || {
    printf 'stop-servers.sh: project path not found: %s\n' "$PROJECT" >&2
    exit 2
  }
fi

# Console scripts, module invocations, and the UltraRAG children the vanilla
# gateway starts from its managed runtime cache.
SCRIPT_PATTERN='(^|/)(research-ultra-rag-mcp|research-ultra-rag-ui|research-ultra-rag-verify|vanilla-ultra-rag-mcp|vanilla-ultra-rag-ui|vanilla-ultra-rag-runtime|memory-ultra-rag-mcp|memory-ultra-rag-ui|graph-memory-ultra-rag-mcp)([[:space:]]|$)'
MODULE_PATTERN='-m (research_ultra_rag_mcp|vanilla_ultra_rag_mcp|memory_ultra_rag_mcp|graph_memory_ultra_rag_mcp)([[:space:]]|$)'
ULTRARAG_PATTERN='vanilla-ultra-rag-mcp/runtime/.*/(corpus|retriever)\.py'

is_server() {
  case "$1" in *stop-servers.sh*) return 1 ;; esac
  printf '%s' "$1" | grep -Eq -e "$SCRIPT_PATTERN" && return 0
  printf '%s' "$1" | grep -Eq -e "$MODULE_PATTERN" && return 0
  printf '%s' "$1" | grep -Eq -e "$ULTRARAG_PATTERN" && return 0
  return 1
}

role_of() {
  # Only the command head identifies the process: a private server carries
  # --vanilla-executable <path>, so matching the whole command line would call it
  # a gateway.
  local head
  head="$(head_of "$1")"
  case "$head" in
    *"vanilla-ultra-rag-mcp/runtime/"*) printf 'ultrarag' ;;
    *research-ultra-rag-ui*|*memory-ultra-rag-ui*|*vanilla-ultra-rag-ui*) printf 'ui' ;;
    *research-ultra-rag-verify*) printf 'verify' ;;
    *vanilla-ultra-rag-mcp*|*vanilla_ultra_rag_mcp*) printf 'gateway' ;;
    *) printf 'server' ;;
  esac
}

head_of() {
  local command="$1" head="" token
  for token in $command; do
    case "$token" in
      --*) break ;;
    esac
    head="$head $token"
  done
  printf '%s' "${head# }"
}

project_of() {
  case "$1" in
    *"--project-root "*)
      printf '%s' "$1" | sed -n 's/.*--project-root \([^ ]*\).*/\1/p'; return ;;
    *"--workspace-root "*)
      printf '%s' "$1" | sed -n 's#.*--workspace-root \([^ ]*\).*#\1#p' \
        | sed 's#/\.research-rag/.*##'; return ;;
  esac
  printf '-'
}

declare -A PARENT=() ARGV=()
while read -r pid ppid args; do
  [ -n "${pid:-}" ] || continue
  PARENT["$pid"]="$ppid"
  ARGV["$pid"]="$args"
done < <(ps -eo pid=,ppid=,args= 2>/dev/null)

CANDIDATES=()
for pid in "${!ARGV[@]}"; do
  is_server "${ARGV[$pid]}" && CANDIDATES+=("$pid")
done

# Depth within the selected family: a top-level server is 0 and anything it owns
# is one deeper, so a server is always signalled before its own children.
in_keep() {
  local candidate
  for candidate in "${KEEP[@]}"; do
    [ "$candidate" = "$1" ] && return 0
  done
  return 1
}

depth_of() {
  local probe="$1" depth=0
  while [ "$depth" -lt 64 ]; do
    probe="${PARENT[$probe]:-0}"
    [ "$probe" != "0" ] || break
    in_keep "$probe" || break
    depth=$((depth + 1))
  done
  printf '%s' "$depth"
}

# With --project, keep the servers that name it and every candidate beneath one,
# so a gateway (matched through its workspace root) and its UltraRAG children
# (matched through the runtime cache path) come along with their server.
ROOTS=()
belongs_to_project() {
  local probe="$1" hops=0 root
  [ "${#ROOTS[@]}" -gt 0 ] || return 1
  while [ "${PARENT[$probe]:-0}" != "0" ] && [ "$hops" -lt 64 ]; do
    probe="${PARENT[$probe]}"
    for root in "${ROOTS[@]}"; do
      [ "$probe" = "$root" ] && return 0
    done
    hops=$((hops + 1))
  done
  return 1
}

KEEP=()
if [ -n "$PROJECT" ]; then
  for pid in "${CANDIDATES[@]}"; do
    case "${ARGV[$pid]}" in *"$PROJECT"*) ROOTS+=("$pid") ;; esac
  done
  for pid in "${CANDIDATES[@]}"; do
    belongs_to_project "$pid" && KEEP+=("$pid")
  done
else
  for pid in "${CANDIDATES[@]}"; do KEEP+=("$pid"); done
fi

# Shallowest first, so a server is signalled before the processes it owns.
ORDERED=()
while read -r _depth pid; do
  ORDERED+=("$pid")
done < <(
  for pid in "${KEEP[@]}"; do
    printf '%s %s\n' "$(depth_of "$pid")" "$pid"
  done | sort -k1,1n -k2,2n
)

if [ "${#ORDERED[@]}" -eq 0 ]; then
  if [ -n "$PROJECT" ]; then
    printf 'No UltraRAG server processes are running for %s.\n' "$PROJECT"
  else
    printf 'No UltraRAG server processes are running.\n'
  fi
  exit 0
fi

printf 'Found %s process(es)%s:\n' "${#ORDERED[@]}" "${PROJECT:+ for $PROJECT}"
printf '  %-8s %-9s %-10s %s\n' 'PID' 'ROLE' 'DEPTH' 'PROJECT'
for pid in "${ORDERED[@]}"; do
  printf '  %-8s %-9s %-10s %s\n' \
    "$pid" "$(role_of "${ARGV[$pid]}")" "$(depth_of "$pid")" "$(project_of "${ARGV[$pid]}")"
done

if [ "$DRY_RUN" = 1 ]; then
  printf '\nDry run: nothing was stopped.\n'
  exit 0
fi

alive() { kill -0 "$1" 2>/dev/null; }

# A PID may exit and be reused between the snapshot and the signal, so confirm
# the process is still one this script recognises before signalling it.
still_ours() {
  local command
  command="$(tr '\0' ' ' < "/proc/$1/cmdline" 2>/dev/null)" || return 1
  [ -n "$command" ] || return 1
  is_server "$command"
}

signal_all() {
  local signal="$1" pid
  for pid in "${ORDERED[@]}"; do
    alive "$pid" || continue
    still_ours "$pid" || continue
    kill "-$signal" "$pid" 2>/dev/null
  done
}

signal_all TERM

waited=0
survivors=${#ORDERED[@]}
while [ "$waited" -lt $((TIMEOUT * 4)) ]; do
  survivors=0
  for pid in "${ORDERED[@]}"; do
    alive "$pid" && survivors=$((survivors + 1))
  done
  [ "$survivors" -eq 0 ] && break
  sleep 0.25
  waited=$((waited + 1))
done

signal_all KILL
sleep 1

failed=0
left=""
for pid in "${ORDERED[@]}"; do
  if alive "$pid"; then
    failed=$((failed + 1))
    left="$left $pid"
    printf '  %-8s %-9s %-10s %s\n' \
      "$pid" "$(role_of "${ARGV[$pid]}")" "$(depth_of "$pid")" 'SURVIVED SIGTERM and SIGKILL'
  fi
done

printf '\nStopped %s of %s process(es).\n' "$(( ${#ORDERED[@]} - failed ))" "${#ORDERED[@]}"
if [ "$failed" -gt 0 ]; then
  printf 'stop-servers.sh: %s process(es) survived:%s\n' "$failed" "$left" >&2
  exit 1
fi
