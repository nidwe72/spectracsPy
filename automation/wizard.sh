#!/usr/bin/env bash
# Foolproof wizard validation run: the pumpkin measurement wizard with the dev-login bypass
# (auto-logs-in a master + pumpkin-plugin virtual session). No arguments needed.
exec "$(dirname "$0")/run.sh" pumpkin_wizard bypass
