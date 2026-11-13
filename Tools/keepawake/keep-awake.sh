#!/usr/bin/env bash
# Tools/keepawake/keep-awake.sh — empêche la veille du poste tant que la forge tourne.
#
# Usage :
#   Tools/keepawake/keep-awake.sh ensure    # arme (ou prolonge le bail) — idempotent
#   Tools/keepawake/keep-awake.sh release   # relâche tout de suite
#   Tools/keepawake/keep-awake.sh status    # dit si le poste est tenu éveillé, et depuis quand
#
# Branché sur des POINTS FIXES, pas sur les playbooks (comme Tools/notify) :
#   - Tools/timing/step.sh start / end  → ensure
#   - Tools/timing/measure.sh           → ensure (avant chaque commande lourde)
#   - step.sh end --status failed, fin de /tech-writer, fin de /merge → release
#     (la forge attend l'humain ou a fini : le poste peut dormir)
#   - fin d'un run /forge               → release
# Aucun agent n'a donc à y penser, et aucun ne peut l'oublier.
#
# Mécanisme : un processus PowerShell détaché (keep-awake.ps1) arme
# SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED) et vit tant que le
# fichier de bail a été touché depuis moins de FORGE_KEEPAWAKE_LEASE_SEC
# (défaut 10800 s = 3 h). Chaque `ensure` touche le bail. Si la forge plante ou
# que la session est coupée, le bail expire et la veille normale revient seule.
# Pourquoi 3 h : au 2026-11-12, le journal (metrics/timings.jsonl, 1 490 étapes)
# montre une plage silencieuse p99 de 71 min à l'intérieur d'une étape, et un
# maximum de 8 h 14 (review de task-437) — un bail de 3 h couvre > 99 % des cas.
#
# Aucun réglage système n'est modifié (pas de powercfg) : l'état retombe avec le
# processus. ES_SYSTEM_REQUIRED n'empêche que la veille sur inactivité ; l'écran
# peut s'éteindre, et fermer le capot ou demander la veille reste possible.
#
# Best-effort, comme le timing et les notifications : sort TOUJOURS en 0, borné
# à ~10 s, n'écrit rien sur stdout sauf pour `status`. Hors Windows : no-op.
#
# Interrupteurs :
#   FORGE_KEEPAWAKE=off             coupe tout (ensure et release ne font rien)
#   FORGE_KEEPAWAKE_LEASE_SEC=N     durée du bail (défaut 10800)
#   FORGE_KEEPAWAKE_POLL_SEC=N      période de contrôle du bail (défaut 60)
#   FORGE_KEEPAWAKE_STATE=dir       répertoire d'état (défaut metrics/.state)
#
# Journal : {state}/keep-awake.log (ARME / RELACHE, avec l'état précédent rendu
# par l'API — « armé » n'est vrai que si cette ligne existe, leçon du banc du
# 2026-08-24 : un « armed » imprimé sans preuve a coûté ~7 h de tir).
# Tests : bash Tools/keepawake/test_keep_awake.sh

set -u

SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

action=${1:-}

[ "${FORGE_KEEPAWAKE:-on}" = "off" ] && [ "$action" != "status" ] && exit 0

case "$(uname -s 2>/dev/null)" in
  MINGW*|MSYS*|CYGWIN*) ;;
  *) [ "$action" = "status" ] && echo "keep-awake : sans objet hors Windows"; exit 0 ;;
esac
command -v powershell.exe >/dev/null 2>&1 || exit 0

# ------------------------------------------------------------------ state
state_dir() {
  if [ -n "${FORGE_KEEPAWAKE_STATE:-}" ]; then
    printf '%s' "$FORGE_KEEPAWAKE_STATE"
    return
  fi
  # shellcheck source=../timing/lib.sh
  . "$SELF_DIR/../timing/lib.sh"
  local root
  root=$(forge_root) || root="$SELF_DIR/../.."
  printf '%s/metrics/.state' "$root"
}

STATE=$(state_dir)
mkdir -p "$STATE" 2>/dev/null || exit 0
PIDF="$STATE/keep-awake.pid"
LEASE="$STATE/keep-awake.lease"
LOG="$STATE/keep-awake.log"
LOCK="$STATE/keep-awake.lock"

LEASE_SEC=${FORGE_KEEPAWAKE_LEASE_SEC:-10800}
POLL_SEC=${FORGE_KEEPAWAKE_POLL_SEC:-60}

winpath() { cygpath -w "$1" 2>/dev/null || printf '%s' "$1"; }

# Vivant = le PID du fichier existe ET c'est un powershell.exe (un PID recyclé
# par un autre programme ne compte pas). `ps` de Git Bash ne voit pas les
# processus Windows non-MSYS : on interroge tasklist.
alive_pid() {
  local p
  p=$(cat "$PIDF" 2>/dev/null | tr -dc '0-9')
  [ -n "$p" ] || return 1
  tasklist //FI "PID eq $p" //NH 2>/dev/null | grep -qi 'powershell' || return 1
  printf '%s' "$p"
}

with_lock() {
  # Verrou mkdir, 5 s max. Sans verrou, on se contente de toucher le bail :
  # un autre appel est en train d'armer.
  local i=0
  while ! mkdir "$LOCK" 2>/dev/null; do
    i=$((i + 1))
    if [ $i -ge 50 ]; then
      # verrou orphelin (> 60 s) : on le reprend
      if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +1 2>/dev/null)" ]; then
        rmdir "$LOCK" 2>/dev/null; continue
      fi
      return 1
    fi
    sleep 0.1
  done
  "$@"
  local rc=$?
  rmdir "$LOCK" 2>/dev/null
  return $rc
}

spawn() {
  rm -f "$PIDF" 2>/dev/null
  local ps1 out
  ps1=$(winpath "$SELF_DIR/keep-awake.ps1")
  # Start-Process : processus Windows indépendant, qui survit à l'appel Bash.
  powershell.exe -NoProfile -NonInteractive -Command \
    "Start-Process -WindowStyle Hidden -FilePath powershell.exe -ArgumentList @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File','\"$ps1\"','-LeaseFile','\"$(winpath "$LEASE")\"','-LogFile','\"$(winpath "$LOG")\"','-PidFile','\"$(winpath "$PIDF")\"','-LeaseSeconds','$LEASE_SEC','-PollSeconds','$POLL_SEC')" \
    >/dev/null 2>&1 || return 1
  # Preuve d'armement : le script écrit son PID puis la ligne ARME. On l'attend.
  local i=0 p
  while [ $i -lt 40 ]; do
    p=$(cat "$PIDF" 2>/dev/null | tr -dc '0-9')
    if [ -n "$p" ] && grep -q "ARME pid=$p " "$LOG" 2>/dev/null; then
      return 0
    fi
    if grep -q "NON ARME" "$LOG" 2>/dev/null && [ -z "$p" ]; then
      return 1
    fi
    sleep 0.25
    i=$((i + 1))
  done
  return 1
}

do_ensure() {
  touch "$LEASE" 2>/dev/null
  alive_pid >/dev/null && return 0
  spawn || echo "$(date -Iseconds) ensure : armement NON prouvé (cf. lignes ci-dessus)" >> "$LOG" 2>/dev/null
  return 0
}

do_release() {
  local p
  rm -f "$LEASE" 2>/dev/null
  p=$(alive_pid) || { rm -f "$PIDF" 2>/dev/null; return 0; }
  # L'état retombe avec le processus : le tuer suffit.
  taskkill //PID "$p" //F >/dev/null 2>&1
  rm -f "$PIDF" 2>/dev/null
  echo "$(date -Iseconds) RELACHE pid=$p : release explicite" >> "$LOG" 2>/dev/null
  return 0
}

do_status() {
  local p age
  if [ "${FORGE_KEEPAWAKE:-on}" = "off" ]; then
    echo "keep-awake : coupé (FORGE_KEEPAWAKE=off)"
    return 0
  fi
  if p=$(alive_pid); then
    age=$(( $(date +%s) - $(date -r "$LEASE" +%s 2>/dev/null || date +%s) ))
    echo "keep-awake : ARMÉ (pid $p) — bail touché il y a ${age} s, expire après ${LEASE_SEC} s sans signe de la forge"
    grep "ARME pid=$p " "$LOG" 2>/dev/null | tail -1
  else
    echo "keep-awake : inactif — le poste suit sa veille normale"
    tail -1 "$LOG" 2>/dev/null
  fi
}

case "$action" in
  ensure)  with_lock do_ensure || touch "$LEASE" 2>/dev/null ;;
  release) with_lock do_release ;;
  status)  do_status ;;
  *) echo "keep-awake.sh: usage: keep-awake.sh {ensure|release|status}" >&2 ;;
esac

exit 0
