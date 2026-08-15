#!/usr/bin/env bash
set -euo pipefail

# Compatibility entry point. Runtime implementation remains centralized.
exec /home/sienna/projects/personal-ai-os/scripts/sync-runtime.sh "$@"
