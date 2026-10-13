#!/usr/bin/env bash
# Collecte locale (repli si GitHub Actions ne peut pas joindre le site).
set -u
cd "$(dirname "$0")/.."
mkdir -p logs
{ date -u +"%F %T UTC"; .venv/bin/python -m bvcsurv.live; echo "code=$?"; } >> logs/collect.log 2>&1
