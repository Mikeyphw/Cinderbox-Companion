#!/usr/bin/env zsh
setopt ERR_EXIT PIPE_FAIL NO_UNSET
local_dir="${0:A:h}"
if ! command -v python3 >/dev/null 2>&1; then
  print -u2 -- 'Python 3 required for the offline HTML preview.'
  exit 2
fi
print -- 'Cinderbox APPROVED dark whole-app portrait mockup'
print -- 'Open in Chrome: http://127.0.0.1:8765/cinderbox-portrait-DARK.html'
print -- 'Press Ctrl+C to stop server.'
cd -- "$local_dir"
exec python3 -m http.server 8765 --bind 127.0.0.1
