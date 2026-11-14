#!/usr/bin/env bash
# Arranque rápido (Linux/macOS). Equivale a: python3 run.py "$@"
cd "$(dirname "$0")" && exec python3 run.py "$@"
