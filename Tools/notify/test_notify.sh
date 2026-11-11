#!/usr/bin/env bash
# Tests de Tools/notify/notify.sh et du hook .claude/hooks/notify-question.sh,
# dans un faux plan de contrôle jetable, avec un faux curl (aucun appel réseau).
#   bash Tools/notify/test_notify.sh
set -u

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REAL_ROOT=$(cd "$HERE/../.." && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT

# Faux plan de contrôle : les outils copiés, des tasks et des questions.
mkdir -p "$T/Tools" "$T/tasks/archived" "$T/questions" "$T/.claude/hooks" "$T/bin"
cp -r "$REAL_ROOT/Tools/notify" "$REAL_ROOT/Tools/tasks" "$REAL_ROOT/Tools/timing" "$T/Tools/"
cp "$REAL_ROOT/.claude/hooks/notify-question.sh" "$T/.claude/hooks/"
touch "$T/CLAUDE.md"
git -C "$T" init -q
N="$T/Tools/notify/notify.sh"

cat > "$T/tasks/done-task-443_recherche_criteres_medicaux.md" <<'EOF'
# task-443
Corps de la task : ne doit jamais partir sur Telegram.
## PRs
- `api-mail` : https://github.com/org/HealthPlatform.Api.Mail/pull/360 — label `awaiting-human-merge`
- `client-mobile` : https://github.com/org/HealthPlatform.Client.Mobile/pull/77 — label `awaiting-human-merge`
- `api-mail` : https://github.com/org/HealthPlatform.Api.Mail/pull/360 — label `awaiting-human-merge`
EOF
touch "$T/tasks/wip-task-40.md"
cat > "$T/questions/task-427.md" <<'EOF'
# task-427 — /review : un critère de la DoD n'est pas tenu à la lettre

**Étape** : `/review`, 2026-11-06 vers 00:50. **Nature** : arbitrage humain.

Détail confidentiel : ne doit jamais partir sur Telegram.
EOF
cat > "$T/questions/task-426.md" <<'EOF'
> ✅ **Résolu le 2026-11-06** : option 1.

# task-426 — question close
EOF

# Faux curl : consigne le texte reçu (lu dans le fichier text@…) et les identifiants.
cat > "$T/bin/curl" <<'EOF'
#!/usr/bin/env bash
for a in "$@"; do
  case "$a" in
    text@*) cat "${a#text@}" >> "$CURL_LOG"; printf '\n--\n' >> "$CURL_LOG" ;;
    chat_id=*) printf '%s\n' "$a" >> "$CURL_LOG.args" ;;
    https://*) printf '%s\n' "$a" >> "$CURL_LOG.args" ;;
  esac
done
printf '%s' "${CURL_REPLY:-{\"ok\":true\}}"
EOF
chmod +x "$T/bin/curl"
export PATH="$T/bin:$PATH" CURL_LOG="$T/curl.log" FORGE_ROOT="$T"
unset TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID FORGE_NOTIFY FORGE_NOTIFY_DRY_RUN
printf 'TELEGRAM_BOT_TOKEN=123456:FAKE_token\r\nTELEGRAM_CHAT_ID=42\r\n' > "$T/creds.env"
export FORGE_TELEGRAM_ENV="$T/creds.env"

fail=0
check() {  # check <libellé> <attendu> <obtenu>
  if [ "$2" = "$3" ]; then echo "ok   - $1"; else echo "FAIL - $1 : attendu [$2], obtenu [$3]"; fail=1; fi
}
has() {  # has <libellé> <motif> <texte>
  case "$3" in *"$2"*) echo "ok   - $1" ;; *) echo "FAIL - $1 : [$2] absent de [$3]"; fail=1 ;; esac
}
hasnt() {
  case "$3" in *"$2"*) echo "FAIL - $1 : [$2] présent dans [$3]"; fail=1 ;; *) echo "ok   - $1" ;; esac
}
dry() { FORGE_NOTIFY_DRY_RUN=1 bash "$N" "$@"; }
reset_log() { rm -f "$CURL_LOG" "$CURL_LOG.args"; }

# --- question
q=$(dry question "$T/questions/task-427.md")
has   "question : id et étape"            "🛑 Arbitrage requis — task-427 (/review)" "$q"
has   "question : titre sans le préfixe"  "un critère de la DoD n'est pas tenu à la lettre" "$q"
hasnt "question : préfixe retiré"         "# task-427" "$q"
hasnt "question : le corps ne part pas"   "confidentiel" "$q"
check "question résolue : silence"        "" "$(dry question "$T/questions/task-426.md")"
check "question absente : silence"        "" "$(dry question "$T/questions/task-999.md")"
check "fichier hors task-* : silence"     "" "$(dry question "$T/CLAUDE.md")"

# --- step
s=$(dry step task-443 review ok)
has   "review ok : PR prête"              "✅ task-443 — PR prête pour votre merge (HAG)" "$s"
has   "review ok : titre du task file"    "recherche criteres medicaux" "$s"
has   "review ok : lien api-mail"         "api-mail : https://github.com/org/HealthPlatform.Api.Mail/pull/360" "$s"
has   "review ok : lien client-mobile"    "client-mobile : https://github.com/org/HealthPlatform.Client.Mobile/pull/77" "$s"
check "review ok : lien dédoublonné"      "1" "$(printf '%s' "$s" | grep -c 'pull/360')"
hasnt "review ok : le corps ne part pas"  "Corps de la task" "$s"
has   "failed : échec annoncé"            "⚠️ task-40 — étape /develop en échec" "$(dry step task-40 develop failed)"
hasnt "failed : task sans titre, pas de ligne vide" $'échec\n\n' "$(dry step task-40 develop failed)"
check "étape ok intermédiaire : silence"  "" "$(dry step task-443 develop ok)"
check "review skipped : silence"          "" "$(dry step task-443 review skipped)"
check "rolled-back : silence"             "" "$(dry step task-443 develop rolled-back)"
check "task '-' : silence"                "" "$(dry step - tech-writer failed)"

# --- interrupteurs
check "FORGE_NOTIFY=off : silence"        "" "$(FORGE_NOTIFY=off FORGE_NOTIFY_DRY_RUN=1 bash "$N" send x)"
reset_log
FORGE_TELEGRAM_ENV="$T/absent.env" bash "$N" send "x"; rc=$?
check "sans identifiants : sort en 0"     "0" "$rc"
check "sans identifiants : aucun appel"   "no" "$( [ -f "$CURL_LOG" ] && echo yes || echo no)"

# --- envoi réel (faux curl) : UTF-8 par fichier, identifiants lus, CRLF retiré
reset_log
bash "$N" send "Accentué é — 🛑"
check "envoi : texte UTF-8 intact"        "Accentué é — 🛑" "$(head -1 "$CURL_LOG")"
check "envoi : chat_id lu"                "chat_id=42" "$(grep chat_id "$CURL_LOG.args")"
# grep et sed retirent les CR à la lecture sous Windows : on compte les octets avec od.
check "envoi : aucun CR transmis à curl"  "0" "$(od -c "$CURL_LOG.args" | grep -c '\\r')"
check "envoi : jeton lu dans le fichier"  "https://api.telegram.org/bot123456:FAKE_token/sendMessage" "$(grep https "$CURL_LOG.args")"
err=$(CURL_REPLY='{"ok":false,"description":"bad bot123456:FAKE_token"}' bash "$N" send x 2>&1 >/dev/null); rc=$?
check "refus Telegram : sort en 0"        "0" "$rc"
has   "refus Telegram : signalé"          "envoi Telegram refusé" "$err"
hasnt "refus Telegram : jeton masqué"     "FAKE_token" "$err"

# --- hook PostToolUse : chemin Windows échappé dans le JSON
reset_log
win=$(printf '%s' "$T/questions/task-427.md" | sed 's#/#\\\\#g')
printf '{"tool_name":"Write","tool_input":{"file_path":"%s","content":"x"}}' "$win" \
  | bash "$T/.claude/hooks/notify-question.sh"; rc=$?
check "hook : sort en 0"                  "0" "$rc"
has   "hook : question notifiée"          "Arbitrage requis — task-427" "$(cat "$CURL_LOG" 2>/dev/null)"
reset_log
printf '{"tool_name":"Write","tool_input":{"file_path":"%s/tasks/x.md"}}' "$T" \
  | bash "$T/.claude/hooks/notify-question.sh"
check "hook : autre fichier, aucun appel" "no" "$( [ -f "$CURL_LOG" ] && echo yes || echo no)"

# --- intégration : step.sh end déclenche la notification
reset_log
bash "$T/Tools/timing/step.sh" end --task task-443 --step review --status ok; rc=$?
check "step.sh end : sort en 0"           "0" "$rc"
has   "step.sh end review ok : notifié"   "PR prête pour votre merge" "$(cat "$CURL_LOG" 2>/dev/null)"
reset_log
bash "$T/Tools/timing/step.sh" end --task task-443 --step sonar --status ok
check "step.sh end sonar ok : silence"    "no" "$( [ -f "$CURL_LOG" ] && echo yes || echo no)"

exit $fail
