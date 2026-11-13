#!/usr/bin/env bash
# Tests de Tools/keepawake/keep-awake.sh et de son branchement sur Tools/timing.
# Vrais processus PowerShell (l'API SetThreadExecutionState est inoffensive),
# état dans un répertoire jetable, faux plan de contrôle pour step.sh/measure.sh.
#   bash Tools/keepawake/test_keep_awake.sh
set -u

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REAL_ROOT=$(cd "$HERE/../.." && pwd)

case "$(uname -s 2>/dev/null)" in
  MINGW*|MSYS*|CYGWIN*) ;;
  *) echo "SKIP : keep-awake ne s'exerce que sous Windows"; exit 0 ;;
esac

T=$(mktemp -d)
K="$HERE/keep-awake.sh"
export FORGE_KEEPAWAKE_STATE="$T/state" FORGE_KEEPAWAKE_POLL_SEC=1 FORGE_KEEPAWAKE_LEASE_SEC=600
unset FORGE_KEEPAWAKE
mkdir -p "$FORGE_KEEPAWAKE_STATE"

cleanup() {
  FORGE_KEEPAWAKE=on bash "$K" release >/dev/null 2>&1
  FORGE_KEEPAWAKE_STATE="$T/fake/metrics/.state" bash "$K" release >/dev/null 2>&1
  rm -rf "$T"
}
trap cleanup EXIT

fail=0
ok()  { echo "ok   - $1"; }
ko()  { echo "FAIL - $1"; fail=1; }
pid() { cat "$FORGE_KEEPAWAKE_STATE/keep-awake.pid" 2>/dev/null | tr -dc '0-9'; }
alive() { [ -n "$1" ] && tasklist //FI "PID eq $1" //NH 2>/dev/null | grep -qi powershell; }
wait_dead() { local i=0; while alive "$1" && [ $i -lt "${2:-40}" ]; do sleep 0.25; i=$((i+1)); done; ! alive "$1"; }

# 1. ensure arme, avec la preuve d'armement dans le journal
out=$(bash "$K" ensure); rc=$?
p1=$(pid)
[ $rc -eq 0 ] && [ -z "$out" ] && ok "ensure sort en 0, silencieux" || ko "ensure : rc=$rc out='$out'"
alive "$p1" && ok "ensure lance un powershell vivant (pid $p1)" || ko "aucun processus vivant après ensure"
grep -q "ARME pid=$p1 flags=0x80000001 etat_precedent=0x" "$FORGE_KEEPAWAKE_STATE/keep-awake.log" \
  && ok "journal : ligne ARME avec l'état précédent rendu par l'API" || ko "journal sans preuve d'armement"
[ -f "$FORGE_KEEPAWAKE_STATE/keep-awake.lease" ] && ok "bail posé" || ko "bail absent"

# 2. ensure est idempotent : même processus, bail retouché
touch -d '-5 minutes' "$FORGE_KEEPAWAKE_STATE/keep-awake.lease"
bash "$K" ensure
[ "$(pid)" = "$p1" ] && ok "ensure idempotent (même pid)" || ko "ensure a relancé un processus : $(pid) au lieu de $p1"
age=$(( $(date +%s) - $(date -r "$FORGE_KEEPAWAKE_STATE/keep-awake.lease" +%s) ))
[ "$age" -lt 10 ] && ok "ensure prolonge le bail" || ko "bail non prolongé (âge $age s)"
[ "$(grep -c '^.*ARME pid=' "$FORGE_KEEPAWAKE_STATE/keep-awake.log")" = "1" ] && ok "une seule ligne ARME" || ko "plusieurs armements"

# 3. status
bash "$K" status | grep -q "ARMÉ (pid $p1)" && ok "status : ARMÉ" || ko "status ne voit pas l'armement"

# 4. release : processus tué, bail retiré, journal
bash "$K" release
wait_dead "$p1" && ok "release tue le processus" || ko "processus $p1 encore vivant après release"
[ ! -f "$FORGE_KEEPAWAKE_STATE/keep-awake.lease" ] && ok "release retire le bail" || ko "bail encore présent"
grep -q "RELACHE pid=$p1 : release explicite" "$FORGE_KEEPAWAKE_STATE/keep-awake.log" && ok "journal : RELACHE" || ko "pas de RELACHE au journal"
bash "$K" status | grep -q "inactif" && ok "status : inactif" || ko "status après release"
bash "$K" release; [ $? -eq 0 ] && ok "release sans processus : no-op en 0" || ko "release à vide"

# 5. pid périmé : ensure relance
echo 999999 > "$FORGE_KEEPAWAKE_STATE/keep-awake.pid"
bash "$K" ensure
p2=$(pid)
[ "$p2" != "999999" ] && alive "$p2" && ok "pid périmé : ensure relance ($p2)" || ko "pid périmé non détecté"
bash "$K" release; wait_dead "$p2"

# 6. le bail expire tout seul (forge plantée, session coupée)
FORGE_KEEPAWAKE_LEASE_SEC=2 bash "$K" ensure
p3=$(pid)
alive "$p3" || ko "bail court : processus non lancé"
wait_dead "$p3" 40 && ok "bail expiré : le processus se relâche seul" || ko "processus $p3 survit au bail expiré"
grep -q "RELACHE pid=$p3 : bail expire" "$FORGE_KEEPAWAKE_STATE/keep-awake.log" && ok "journal : RELACHE bail expire" || ko "pas de RELACHE sur expiration"
[ ! -f "$FORGE_KEEPAWAKE_STATE/keep-awake.pid" ] && ok "fichier pid retiré à l'expiration" || ko "fichier pid orphelin"

# 7. interrupteur
rm -f "$FORGE_KEEPAWAKE_STATE"/keep-awake.*
FORGE_KEEPAWAKE=off bash "$K" ensure
[ ! -f "$FORGE_KEEPAWAKE_STATE/keep-awake.pid" ] && ok "FORGE_KEEPAWAKE=off : rien n'est armé" || { ko "armé malgré off"; bash "$K" release; }
FORGE_KEEPAWAKE=off bash "$K" status | grep -q "coupé" && ok "status signale l'interrupteur" || ko "status ignore l'interrupteur"

# 8. branchement sur Tools/timing (faux plan de contrôle : le vrai journal n'est pas touché)
F="$T/fake"
mkdir -p "$F/Tools" "$F/tasks" "$F/metrics"
cp -r "$REAL_ROOT/Tools/timing" "$REAL_ROOT/Tools/keepawake" "$F/Tools/"
touch "$F/CLAUDE.md"
export FORGE_ROOT="$F" FORGE_NOTIFY=off
unset FORGE_KEEPAWAKE_STATE   # défaut : {forge root}/metrics/.state
FS="$F/metrics/.state"
fpid() { cat "$FS/keep-awake.pid" 2>/dev/null | tr -dc '0-9'; }

bash "$F/Tools/timing/step.sh" start --task task-999 --step develop
q1=$(fpid)
alive "$q1" && ok "step.sh start arme le keep-awake" || ko "step.sh start n'arme pas"

bash "$F/Tools/timing/step.sh" end --task task-999 --step develop --status ok
[ "$(fpid)" = "$q1" ] && alive "$q1" && ok "step.sh end ok : reste armé" || ko "step.sh end ok a relâché"

bash "$F/Tools/timing/step.sh" end --task task-999 --step e2e --status failed
wait_dead "$q1" && ok "step.sh end failed : relâché (la forge attend l'humain)" || ko "toujours armé après un échec"

bash "$F/Tools/timing/measure.sh" --task task-999 --step develop --kind other -- true
q2=$(fpid)
alive "$q2" && ok "measure.sh arme le keep-awake" || ko "measure.sh n'arme pas"

out=$(bash "$F/Tools/timing/measure.sh" --task task-999 --step develop --kind other -- sh -c 'echo SORTIE; exit 7'); rc=$?
[ "$out" = "SORTIE" ] && [ $rc -eq 7 ] && ok "measure.sh reste transparent (sortie et code retour)" || ko "measure.sh : out='$out' rc=$rc"

bash "$F/Tools/timing/step.sh" start --task task-999 --step tech-writer
[ "$(fpid)" = "$q2" ] && alive "$q2" || ko "armement perdu avant /tech-writer"
bash "$F/Tools/timing/step.sh" end --task task-999 --step tech-writer --status ok
wait_dead "$q2" && ok "fin de /tech-writer : relâché (fin de cycle)" || ko "toujours armé après /tech-writer"

bash "$F/Tools/timing/step.sh" start --task task-999 --step merge
q3=$(fpid)
alive "$q3" || ko "step.sh start merge n'arme pas"
bash "$F/Tools/timing/step.sh" end --task task-999 --step merge --status ok
wait_dead "$q3" && ok "fin de /merge : relâché" || ko "toujours armé après /merge"

echo
[ $fail -eq 0 ] && echo "TOUS LES TESTS PASSENT" || echo "ÉCHECS"
exit $fail
