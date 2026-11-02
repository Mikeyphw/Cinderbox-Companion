#!/data/data/com.termux/files/usr/bin/zsh
# Read-only: identify actual symlink components on paths relevant to Cinderbox.
# No chmod, mkdir, deletion, reset, or app data file reads.
setopt errexit pipefail
print -- 'CINDERBOX STORAGE PATH COMPONENT DIAGNOSTIC (READ-ONLY)'
print -- 'This is the su shell mount namespace, which may differ from the app.'
su -c '
for root in \
  /storage/emulated/0/StardewValley/desktop/Mods \
  /storage/emulated/0/StardewValley/smapi-internal \
  /storage/emulated/0/Download \
  /data/user/0/com.sdvsync/cache; do
  printf "\nDESTINATION: %s\n" "$root"
  cursor="$root"
  found=0
  while :; do
    if [ -L "$cursor" ]; then
      printf "  SYMLINK COMPONENT: %s -> " "$cursor"
      readlink "$cursor" || true
      found=1
    fi
    [ "$cursor" = / ] && break
    cursor="${cursor%/*}"
    [ -n "$cursor" ] || cursor=/
  done
  [ "$found" -eq 1 ] || printf "  No symlink component visible to su on this path\n"
done
'
