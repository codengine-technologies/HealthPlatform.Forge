#!/usr/bin/env bash
# Tools/notify/notify.sh — notifications Telegram de la forge.
#
# Prévient l'humain des deux moments où la forge l'attend : une question
# d'arbitrage (questions/task-*.md) et une PR prête pour le merge (HAG). Prévient
# aussi d'une étape en échec et de la fin d'un run /forge.
#
# Usage :
#   Tools/notify/notify.sh send "texte libre"             # fin de run /forge
#   Tools/notify/notify.sh question questions/task-427.md  # hook PostToolUse (Write)
#   Tools/notify/notify.sh step task-443 review ok         # appelé par Tools/timing/step.sh end
#
# Règles de `step` : review + ok → PR prête ; tout étape + failed → échec ;
# le reste (skipped, rolled-back, étapes ok intermédiaires) ne notifie pas.
#
# Identifiants : TELEGRAM_BOT_TOKEN et TELEGRAM_CHAT_ID, pris dans
# l'environnement, sinon dans le fichier ${FORGE_TELEGRAM_ENV:-$HOME/.forge-telegram.env}
# (lignes CLE=valeur, lu sans être exécuté). Hors dépôt, jamais commité.
#
# Données envoyées : identifiant et titre de la task, étape, statut, titre de la
# question, liens des PRs. JAMAIS le corps d'une question ni d'un task file :
# Telegram est un service externe.
#
# Interrupteurs :
#   FORGE_NOTIFY=off          aucune notification
#   FORGE_NOTIFY_DRY_RUN=1    écrit le message sur stdout au lieu de l'envoyer (tests)
#
# Comme Tools/timing/, la notification ne casse JAMAIS une étape : tous les
# chemins sortent en 0, curl est borné à 5 s.

set -u

SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

forge_root() {
  if [ -n "${FORGE_ROOT:-}" ] && [ -d "$FORGE_ROOT/tasks" ]; then
    printf '%s' "$FORGE_ROOT"
  else
    (cd "$SELF_DIR/../.." && pwd)
  fi
}

# ------------------------------------------------------------ identifiants
load_credentials() {
  local f=${FORGE_TELEGRAM_ENV:-$HOME/.forge-telegram.env} key val
  [ -f "$f" ] || return 0
  while IFS='=' read -r key val; do
    val=${val%$'\r'}
    case "$key" in
      TELEGRAM_BOT_TOKEN) [ -n "${TELEGRAM_BOT_TOKEN:-}" ] || TELEGRAM_BOT_TOKEN=$val ;;
      TELEGRAM_CHAT_ID)   [ -n "${TELEGRAM_CHAT_ID:-}" ]   || TELEGRAM_CHAT_ID=$val ;;
    esac
  done < "$f"
}

# ------------------------------------------------------------------- envoi
send() {
  local text=$1
  [ "${FORGE_NOTIFY:-on}" = "off" ] && return 0
  if [ "${FORGE_NOTIFY_DRY_RUN:-0}" = "1" ]; then
    printf '%s\n' "$text"
    return 0
  fi
  load_credentials
  if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
    return 0   # non configuré : silence, comme un poste sans bot
  fi
  # Le texte passe par un fichier : sous Git Bash, curl reçoit ses arguments dans
  # la page de code ANSI et Telegram refuse (« strings must be encoded in UTF-8 »).
  # Après `@`, MSYS ne convertit pas le chemin : d'où cygpath -m.
  local msg resp
  msg=$(mktemp 2>/dev/null) || return 0
  printf '%s' "$text" > "$msg"
  local msg_path=$msg
  command -v cygpath >/dev/null 2>&1 && msg_path=$(cygpath -m "$msg")
  resp=$(curl -sS --max-time 5 "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text@${msg_path}" \
    --data-urlencode 'link_preview_options={"is_disabled":true}' 2>&1)
  rm -f "$msg"
  case "$resp" in
    *'"ok":true'*) ;;
    *) printf 'notify.sh: envoi Telegram refusé : %s\n' \
         "$(printf '%s' "$resp" | sed -E 's/bot[0-9]+:[A-Za-z0-9_-]+/bot<token>/g' | head -c 200)" >&2 ;;
  esac
  return 0
}

# ------------------------------------------------------------ task files
task_title() {  # titre lisible tiré du nom du task file, vide si sans titre
  local p
  p=$(FORGE_ROOT=$(forge_root) bash "$SELF_DIR/../tasks/task-file.sh" path "$1" 2>/dev/null) || return 0
  p=$(basename "$p" .md)
  case "$p" in
    *_*) printf '%s' "${p#*_}" | tr '_' ' ' ;;
  esac
}

pr_links() {  # liens des PRs consignés par /review (« - `repo` : https://…/pull/N »)
  local p root
  root=$(forge_root)
  p=$(FORGE_ROOT=$root bash "$SELF_DIR/../tasks/task-file.sh" path "$1" 2>/dev/null) || return 0
  grep -oE '^- `[a-z-]+` : https://github\.com/[^ ]+/pull/[0-9]+' "$root/$p" 2>/dev/null \
    | sed -E 's/^- `([a-z-]+)` : /\1 : /' | awk '!seen[$0]++' | head -8
}

# --------------------------------------------------------------- messages
cmd_question() {
  local f=$1 id h1 step
  [ -f "$f" ] || return 0
  id=$(basename "$f" .md)
  case "$id" in task-[0-9]*) ;; *) return 0 ;; esac
  # Une question déjà résolue réécrite ne réveille personne.
  head -5 "$f" | grep -q 'Résolu' && return 0
  h1=$(grep -m1 -E '^# ' "$f" | sed -E 's/^# +//; s/^task-[0-9]+ *[—:-] *//' | cut -c1-160)
  step=$(grep -m1 -oE '\*\*Étape\*\* *: *`/[a-z-]+`' "$f" | grep -oE '/[a-z-]+')
  send "🛑 Arbitrage requis — ${id}${step:+ (${step})}
${h1:-question sans titre}
→ questions/${id}.md"
}

cmd_step() {
  local task=$1 step=$2 status=$3 title
  case "$task" in task-[0-9]*) ;; *) return 0 ;; esac
  title=$(task_title "$task")
  if [ "$status" = "failed" ]; then
    send "⚠️ ${task} — étape /${step} en échec${title:+
${title}}
→ voir questions/${task}.md s'il existe"
  elif [ "$step" = "review" ] && [ "$status" = "ok" ]; then
    local prs
    prs=$(pr_links "$task")
    send "✅ ${task} — PR prête pour votre merge (HAG)${title:+
${title}}${prs:+

${prs}}"
  fi
}

action=${1:-}
[ $# -gt 0 ] && shift
case "$action" in
  send)     [ -n "${1:-}" ] && send "$1" ;;
  question) [ -n "${1:-}" ] && cmd_question "$1" ;;
  step)     [ $# -ge 3 ] && cmd_step "$1" "$2" "$3" ;;
  *) echo "notify.sh: usage: notify.sh {send TEXTE|question FICHIER|step TASK ETAPE STATUT}" >&2 ;;
esac
exit 0
