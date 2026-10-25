#!/usr/bin/env bash
# Tools/tasks/task-file.sh — le seul endroit qui sait où vit un task file.
#
# Un task file porte un titre depuis le 2026-10-25 :
#   tasks/todo-task-400_delegation_tracer_ce_qui_agit.md
# L'identifiant (`task-400`) reste la seule clé ; le titre est un repère pour le
# développeur, fixé une fois pour toutes par /po. Les fichiers plus anciens, sans
# titre (`tasks/todo-task-369.md`), restent valides : on ne renomme pas l'existant.
#
# Le `_` qui suit l'identifiant est le séparateur : `wip-task-40_*` ne peut pas
# attraper `wip-task-400_…`, ce qu'un tiret ne garantirait pas.
#
# Usage (toujours depuis n'importe où, les chemins rendus sont relatifs à la racine) :
#   Tools/tasks/task-file.sh path   task-400 [état…]   # chemin du task file
#   Tools/tasks/task-file.sh move   task-400 done      # git mv vers l'état, titre conservé
#   Tools/tasks/task-file.sh name   task-400 "Délégation : tracer ce qui agit"
#                                                       # -> todo-task-400_delegation_tracer_ce_qui_agit.md
#   Tools/tasks/task-file.sh slug   "Délégation : tracer ce qui agit" [max]
#   Tools/tasks/task-file.sh branch-slug task-400       # titre du fichier, en slug de branche (40 car.)
#
# États : todo | wip | review | done | archived (archived vit dans tasks/archived/).
# Codes : 0 trouvé / fait, 1 absent, 2 ambigu (plusieurs fichiers pour le même id),
#         64 usage.

set -u

TITLE_MAX=100     # longueur maximale du titre (la partie après le `_`)
BRANCH_MAX=40     # longueur maximale du slug de branche (feat/{task-id}-{slug})
STATES="wip review done todo archived"

forge_root() {
  if [ -n "${FORGE_ROOT:-}" ] && [ -d "$FORGE_ROOT/tasks" ]; then
    printf '%s' "$FORGE_ROOT"
    return 0
  fi
  (cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
}

state_dir() {
  case "$1" in
    archived) printf 'tasks/archived' ;;
    todo|wip|review|done) printf 'tasks' ;;
    *) return 1 ;;
  esac
}

# slug <texte> [max] — ASCII minuscule, mots séparés par `_`, coupé sur un mot.
slug() {
  local max=${2:-$TITLE_MAX} s
  # Les vraies apostrophes du titre séparent des mots (« l'œuvre ») : espace AVANT iconv.
  s=$(printf '%s' "$1" | sed -e "s/'/ /g" -e "s/’/ /g")
  s=$(printf '%s' "$s" | iconv -f UTF-8 -t ASCII//TRANSLIT 2>/dev/null || printf '%s' "$s")
  # La translittération d'iconv marque l'accent à part (« é » → « 'e », « où » → « o`u ») :
  # ces marques sont retirées AVANT le découpage, sinon « délégation » devient « d_el_egation ».
  s=$(printf '%s' "$s" | tr -d "'\`^\"~" | tr '[:upper:]' '[:lower:]' \
        | sed -e 's/[^a-z0-9]\{1,\}/_/g' -e 's/^_//' -e 's/_$//')
  if [ "${#s}" -gt "$max" ]; then
    if [ "${s:$max:1}" = "_" ]; then
      s=${s:0:$max}
    else
      s=${s:0:$max}
      case "$s" in *_*) s=${s%_*} ;; esac
    fi
  fi
  printf '%s' "${s%_}"
}

# matches <id> [états…] — un chemin relatif par ligne, dans l'ordre des états.
matches() {
  local id=$1 root st dir f
  shift
  root=$(forge_root) || return 1
  [ $# -gt 0 ] || set -- $STATES
  for st in "$@"; do
    dir=$(state_dir "$st") || { echo "task-file.sh: état inconnu '$st'" >&2; return 64; }
    for f in "$root/$dir/$st-$id.md" "$root/$dir/$st-${id}_"*.md; do
      [ -f "$f" ] && printf '%s\n' "${f#"$root"/}"
    done
  done
  return 0
}

cmd_path() {
  local id=${1:-} found n
  [ -n "$id" ] || { echo "usage: task-file.sh path {task-id} [état…]" >&2; return 64; }
  shift
  found=$(matches "$id" "$@") || return $?
  n=$(printf '%s' "$found" | grep -c . || true)
  if [ "$n" -eq 0 ]; then
    echo "task-file.sh: aucun task file pour '$id'${1:+ (états : $*)}" >&2
    return 1
  fi
  if [ "$n" -gt 1 ]; then
    echo "task-file.sh: plusieurs task files pour '$id' :" >&2
    printf '%s\n' "$found" | sed 's/^/  /' >&2
    return 2
  fi
  printf '%s\n' "$found"
}

cmd_move() {
  local id=${1:-} target=${2:-} root cur base rest dir new
  [ -n "$id" ] && [ -n "$target" ] || { echo "usage: task-file.sh move {task-id} {état}" >&2; return 64; }
  dir=$(state_dir "$target") || { echo "task-file.sh: état inconnu '$target'" >&2; return 64; }
  root=$(forge_root) || return 1
  cur=$(cmd_path "$id") || return $?
  base=${cur##*/}
  rest=${base#*-}                      # "{id}[_titre].md" : le préfixe d'état saute
  new="$dir/$target-$rest"
  if [ "$cur" = "$new" ]; then
    printf '%s\n' "$new"
    return 0
  fi
  mkdir -p "$root/$dir"
  if git -C "$root" ls-files --error-unmatch -- "$cur" >/dev/null 2>&1; then
    git -C "$root" mv -- "$cur" "$new" || return 1
  else
    mv -- "$root/$cur" "$root/$new" || return 1
  fi
  printf '%s\n' "$new"
}

cmd_name() {
  local id=${1:-} title=${2:-} s
  [ -n "$id" ] && [ -n "$title" ] || { echo "usage: task-file.sh name {task-id} \"{titre}\"" >&2; return 64; }
  s=$(slug "$title")
  [ -n "$s" ] || { echo "task-file.sh: titre vide après normalisation" >&2; return 64; }
  printf 'todo-%s_%s.md\n' "$id" "$s"
}

cmd_branch_slug() {
  local id=${1:-} cur base title
  [ -n "$id" ] || { echo "usage: task-file.sh branch-slug {task-id}" >&2; return 64; }
  cur=$(cmd_path "$id") || return $?
  base=${cur##*/}
  base=${base%.md}
  case "$base" in
    *-"$id"_*) title=${base#*-"$id"_} ;;
    *) return 1 ;;                     # ancien nom, sans titre : /start dérive le slug du corps
  esac
  slug "$(printf '%s' "$title" | tr '_' ' ')" "$BRANCH_MAX" | tr '_' '-'
  echo
}

action=${1:-}
[ $# -gt 0 ] && shift
case "$action" in
  path)        cmd_path "$@" ;;
  move)        cmd_move "$@" ;;
  name)        cmd_name "$@" ;;
  slug)        [ $# -ge 1 ] || { echo "usage: task-file.sh slug \"{titre}\" [max]" >&2; exit 64; }
               slug "$@"; echo ;;
  branch-slug) cmd_branch_slug "$@" ;;
  *) sed -n '2,25p' "${BASH_SOURCE[0]}" >&2; exit 64 ;;
esac
