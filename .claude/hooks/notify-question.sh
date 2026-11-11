#!/usr/bin/env bash
# Hook PostToolUse (matcher Write) — prévient l'humain sur Telegram quand la
# chaîne écrit une question d'arbitrage : questions/task-*.md.
#
# Pur bash : appelé après chaque Write, il ne doit dépendre ni de python ni de jq.
# Ne bloque jamais rien : sort toujours en 0. Envoi : Tools/notify/notify.sh.

INPUT=$(cat)

# "file_path":"d:\\TechWatch\\HealthPlatform\\questions\\task-427.md" → d:/TechWatch/…/questions/task-427.md
path=$(printf '%s' "$INPUT" | grep -oE '"file_path" *: *"[^"]*"' | head -1 \
  | sed -E 's/^"file_path" *: *"//; s/"$//; s#\\\\#/#g; s#\\#/#g')

case "$path" in
  */questions/task-[0-9]*.md) ;;
  *) exit 0 ;;
esac

# Le notifieur du plan de contrôle qui porte ce dossier questions/.
root=${path%/questions/*}
notifier="$root/Tools/notify/notify.sh"
[ -f "$notifier" ] || exit 0
FORGE_ROOT=$root bash "$notifier" question "$path" >/dev/null 2>&1 || true
exit 0
