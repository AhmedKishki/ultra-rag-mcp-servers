#!/usr/bin/env bash
# Stop every UltraRAG MCP server, browser UI, gateway, and UltraRAG child that
# this collection started, and nothing else.
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
# The decisions are made in collection_processes.py beside this file, because a
# process is identified by its NUL-separated /proc argv and its start time, and
# shell word splitting destroys both. Each process is then reached through a
# pidfd, which needs Linux 5.3 or newer and Python 3.9 or newer: without one
# nothing is signalled and the run exits 3 saying so, because a PID on its own
# cannot be signalled without risking a process that has since reused it. A
# dry run needs no pidfd. This script resolves the directory and hands over the
# arguments, so the command line and its refusals stay the same. Set PYTHON to
# choose the interpreter.
#
# Exit 0 when everything chosen stopped, 1 when a process survived both signals,
# 2 for a refused command line, and 3 when no process could be signalled safely.
set -uo pipefail

here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)" || exit 1
helper="$here/collection_processes.py"
python="${PYTHON:-python3}"

if [ ! -f "$helper" ]; then
  printf 'stop-servers.sh: missing helper: %s\n' "$helper" >&2
  exit 1
fi
if ! command -v "$python" >/dev/null 2>&1; then
  printf 'stop-servers.sh: no interpreter: %s\n' "$python" >&2
  exit 1
fi

exec "$python" "$helper" "$@"