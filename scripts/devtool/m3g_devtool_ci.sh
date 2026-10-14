#!/bin/sh
# Devtool ACTIONS-05 front end. Never merges, signs release, publishes, or installs.
set -eu
repo=$(CDPATH= cd -- "${CINDERBOX_REPO:-$HOME/Code/Cinderbox-Companion}" && pwd)
branch=feature/m3g-steam-reliability-observability
repoid=Mikeyphw/Cinderbox-Companion
cmd=${1:-plan}
shift || true
command -v devtool >/dev/null 2>&1 || { echo 'Install Devtool first' >&2; exit 127; }
case "$cmd" in
  plan)
    exec devtool -r "$repo" actions android plan --github-repo "$repoid" \
      --module app --variant debug --format apk --ref "$branch" --json
    ;;
  run)
    # Explicit invocation means explicit dispatch consent; no unattended mutation.
    exec devtool -r "$repo" actions android run --github-repo "$repoid" \
      --module app --variant debug --format apk --ref "$branch" --yes --json
    ;;
  watch)
    [ "$#" -eq 1 ] || { echo 'Usage: m3g_devtool_ci.sh watch RUN_ID' >&2; exit 2; }
    exec devtool -r "$repo" actions watch --github-repo "$repoid" \
      --run-id "$1" --max-checks 30 --interval 10 --json
    ;;
  artifacts)
    [ "$#" -eq 1 ] || { echo 'Usage: m3g_devtool_ci.sh artifacts RUN_ID' >&2; exit 2; }
    exec devtool -r "$repo" actions artifacts --github-repo "$repoid" --run-id "$1" --json
    ;;
  collect)
    [ "$#" -eq 2 ] || { echo 'Usage: m3g_devtool_ci.sh collect RUN_ID ARTIFACT_ID' >&2; exit 2; }
    exec devtool -r "$repo" actions android collect --github-repo "$repoid" \
      --run-id "$1" --artifact-id "$2" --format apk --variant debug \
      --expected-package com.sdvsync --download --json
    ;;
  *) echo 'Usage: m3g_devtool_ci.sh {plan|run|watch RUN_ID|artifacts RUN_ID|collect RUN_ID ARTIFACT_ID}' >&2; exit 2 ;;
esac
