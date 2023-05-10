#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

BOLD="\e[1m"
RED="\e[31m"
RESET="\e[0m"

function cleanup() {
  TEMPDIR="${APPDIR:-}"
  if [[ -n "$TEMPDIR" ]] && [[ -d "$TEMPDIR" ]]; then
    rm -Rf "$TEMPDIR"
  fi
}
trap cleanup ERR EXIT

function log() {
  echo -en "${BOLD}" >/dev/stderr
  echo -n '[+]' "$1" >/dev/stderr
  echo -e "${RESET}" >/dev/stderr
}

function log_err() {
  echo -en "${BOLD}${RED}" >/dev/stderr
  echo -n '[!]' "$1" >/dev/stderr
  echo -e "${RESET}" >/dev/stderr
}

function log2() {
  echo -en "${BOLD}" >/dev/stderr
  echo -n '[+]' "${1}" >/dev/stderr
  echo -en "${RESET} " >/dev/stderr
  echo "${2}"
}

ORCHESTRA_DOTDIR=""
APPIMAGETOOL="./appimagetool-x86_64.AppImage"
APPIMAGE_NAME="orc_toolbox"
APPIMAGE_TITLE="Orchestra Toolbox"
APPIMAGE_DESC="A collection of tools from orchestra"
OUTPUT="$APPIMAGE_NAME.AppImage"
ICON="$SCRIPT_DIR/revng_logo.png"
COMPRESS=0

function usage() {
  echo "Usage: $0 [-a path/to/appimagetool-x86_64.AppImage] [-o path/to/output.AppImage] [-d ORCHESTRA_DOTDIR] [-n 'AppImage name'] [-t 'AppImage title'] [-D 'AppImage description'] [-i path/to/icon.png] [-c]"
  echo "Packs an orchestra root directory into an AppImage."
  exit 1
}

while getopts "a:o:d:n:t:D:i:ch" arg; do
  case "$arg" in
  a)
    APPIMAGETOOL="$OPTARG"
    ;;
  c)
    COMPRESS=1
    ;;
  d)
    ORCHESTRA_DOTDIR="$OPTARG"
    ;;
  o)
    OUTPUT="$OPTARG"
    ;;
  n)
    APPIMAGE_NAME="$OPTARG"
    ;;
  t)
    APPIMAGE_TITLE="$OPTARG"
    ;;
  D)
    APPIMAGE_DESC="$OPTARG"
    ;;
  i)
    ICON="$OPTARG"
    ;;
  *)
    usage
    ;;
  esac
done

if [[ ! -x "$APPIMAGETOOL" ]]; then
  log_err "appimagetool '$APPIMAGETOOL' does not exist or is not executable"
  log2 "Note:" "You can download appimagetool-x86_64.AppImage from https://github.com/AppImage/AppImageKit/releases"
  usage
fi
if [[ ! -f "$ICON" ]]; then
  log_err "Icon does not exist: '$ICON'"
  usage
fi

log2 "Using appimagetool:" "$APPIMAGETOOL"

if [[ -z "$ORCHESTRA_DOTDIR" ]]; then
  ORC=("orc")
else
  ORC=("orc" "--orchestra-dotdir" "$ORCHESTRA_DOTDIR")
fi

ORC_ENV="$("${ORC[@]}" environment)"
ORCHESTRA_ROOT=""
eval "$(echo "$ORC_ENV" | grep '^export ORCHESTRA_ROOT=')"

log2 "Found orchestra root:" "$ORCHESTRA_ROOT"

log "Creating AppDir..."
APPDIR="$(mktemp -d -p "$PWD" --suffix=".AppDir")"
rmdir "$APPDIR"
cp -a --reflink=auto "$ORCHESTRA_ROOT" "$APPDIR"

ICON_EXT="${ICON##*.}"
cp "$ICON" "$APPDIR/$APPIMAGE_NAME.$ICON_EXT"

cat >"$APPDIR/$APPIMAGE_NAME.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APPIMAGE_TITLE
Icon=$APPIMAGE_NAME
Exec=AppRun
Categories=Development
EOF

mkdir -p "$APPDIR/usr/share/applications"
cp "$APPDIR/$APPIMAGE_NAME.desktop" "$APPDIR/usr/share/applications/$APPIMAGE_NAME.desktop"

APPRUN="$APPDIR/AppRun"

{
  cat <<'EOF'
#!/bin/bash
set -euo pipefail

export ORCHESTRA_ROOT="$APPDIR"
EOF

  echo "$ORC_ENV" | grep -v '^export ORCHESTRA_ROOT=\|^export GIT_ASKPASS=\|^export SOURCE_ARCHIVES=\|^export BINARY_ARCHIVES=\|^export SOURCES_DIR=\|^export BUILDS_DIR=\|^export TMP_ROOTS=\|^unset'

  cat <<'EOF'

ARG0_FNAME="$(basename "$ARGV0")"
APPIMAGE_FNAME="$(basename "$APPIMAGE")"

if [[ "$ARG0_FNAME" != "$APPIMAGE_FNAME" ]]; then
  # User symlinked the AppImage to something else - behave like busybox
  CMD_ARG0="$ARG0_FNAME"
  CMD_ARGS=("$ARG0_FNAME" "$@")
else
  # User is running ./foo.AppImage command
  if [[ "$#" == 0 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
EOF
  cat <<EOF
    echo "$APPIMAGE_TITLE - $APPIMAGE_DESC"
EOF
  cat <<'EOF'
    echo "Usage: $ARGV0 [toolname] [args...]" >&2
    echo "You may also symlink the AppImage to a tool name to create a shortcut."
    echo "Pass --appimage-help for help specific to the AppImage runtime."
    exit 1
  fi
  CMD_ARG0="$1"
  CMD_ARGS=("$@")
fi

if [[ -z "$CMD_ARG0" ]]; then
  echo "Invalid ARGV0" >&2
  exit 1
fi

CMD_PATH="$(which "$CMD_ARG0" 2>/dev/null)"
if [[ -z "${FORCE_RUN_OUTSIDE_APPIMAGE:-}" ]]; then
  if [[ -z "$CMD_PATH" ]] || [[ "$CMD_PATH" != "$APPDIR"* ]]; then
    echo "Error: Could not find '$CMD_ARG0' inside AppImage! (found candidate: '$CMD_PATH')" >&2
    exit 2
  fi
fi

exec -a "$CMD_ARG0" "${CMD_ARGS[@]}"

EOF
} >"$APPRUN"

chmod +x "$APPRUN"

log "Packing AppImage..."
COMP_ARGS=()
if [[ "$COMPRESS" != 0 ]]; then
    COMP_ARGS=(--comp xz)
fi
ARCH=x86_64 "$APPIMAGETOOL" -n "${COMP_ARGS[@]}" "$APPDIR" "$OUTPUT"

echo
log2 "AppImage is ready at:" "$OUTPUT"
