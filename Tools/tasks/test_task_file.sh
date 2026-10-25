#!/usr/bin/env bash
# Tests de Tools/tasks/task-file.sh — dans un faux plan de contrôle jetable.
#   bash Tools/tasks/test_task_file.sh
set -u

SELF=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/task-file.sh
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
export FORGE_ROOT=$T
mkdir -p "$T/tasks/archived"
git -C "$T" init -q
git -C "$T" -c user.email=t@t -c user.name=t commit -q --allow-empty -m init

fail=0
check() {  # check <libellé> <attendu> <obtenu>
  if [ "$2" = "$3" ]; then echo "ok   - $1"; else echo "FAIL - $1 : attendu [$2], obtenu [$3]"; fail=1; fi
}

# --- slug / name
check "slug : accents, ponctuation, casse" "delegation_tracer_ce_qui_agit" \
  "$(bash "$SELF" slug 'Délégation : tracer « ce qui » agit')"
check "slug : l'apostrophe sépare deux mots" "l_oeuvre_ou_ca_va" "$(bash "$SELF" slug "L'Œuvre — où ça va ?")"
check "slug : coupé sur un mot" "un_deux" "$(bash "$SELF" slug 'un deux troisieme' 9)"
check "slug : coupe tombant sur le séparateur" "un_deux" "$(bash "$SELF" slug 'un deux trois' 7)"
long=$(bash "$SELF" slug "$(printf 'mot%.0s ' $(seq 1 60))")
[ "${#long}" -le 100 ]; check "slug : 100 caractères au plus" "0" "$?"
check "name" "todo-task-400_delegation_tracer_ce_qui_agit.md" \
  "$(bash "$SELF" name task-400 'Délégation : tracer ce qui agit')"

# --- path : deux formes, pas de collision de préfixe
touch "$T/tasks/todo-task-40.md" "$T/tasks/todo-task-400_delegation_tracer.md"
git -C "$T" add tasks && git -C "$T" -c user.email=t@t -c user.name=t commit -q -m tasks
check "path : nom titré" "tasks/todo-task-400_delegation_tracer.md" "$(bash "$SELF" path task-400)"
check "path : ancien nom, sans collision avec task-400" "tasks/todo-task-40.md" "$(bash "$SELF" path task-40)"
bash "$SELF" path task-4 2>/dev/null; check "path : absent → 1" "1" "$?"
bash "$SELF" path task-400 wip 2>/dev/null; check "path : filtré sur un autre état → 1" "1" "$?"

# --- move : titre conservé, git mv
check "move todo → wip" "tasks/wip-task-400_delegation_tracer.md" "$(bash "$SELF" move task-400 wip)"
check "move : suivi par git" "R" "$(git -C "$T" status --porcelain | grep -o '^R' | head -1)"
check "move wip → archived" "tasks/archived/archived-task-400_delegation_tracer.md" "$(bash "$SELF" move task-400 archived)"
check "move ancien nom → done" "tasks/done-task-40.md" "$(bash "$SELF" move task-40 done)"

# --- branch-slug
check "branch-slug : titre en tirets" "delegation-tracer" "$(bash "$SELF" branch-slug task-400)"
bash "$SELF" branch-slug task-40 >/dev/null; check "branch-slug : ancien nom → 1" "1" "$?"

# --- ambiguïté
touch "$T/tasks/todo-task-500.md" "$T/tasks/wip-task-500_x.md"
bash "$SELF" path task-500 2>/dev/null; check "path : deux fichiers pour un id → 2" "2" "$?"

exit $fail
