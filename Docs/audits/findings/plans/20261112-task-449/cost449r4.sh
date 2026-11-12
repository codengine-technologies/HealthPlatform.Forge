#!/usr/bin/env bash
# task-449 reprise 4 (S2) — coût SQL des critères tapés « De » / « Objet » / « À », avant (ILIKE de develop) et après
# (mots normalisés par search_normalize, en début de mot), sur la copie srch_lab de la boîte de formation.
# Forme de la requête : page de 51 de l'INBOX par date, comme la recherche par critères. 3 chauffes, 20 mesures.
N=20
run() { # $1 libellé, $2 condition
  local sql="EXPLAIN (ANALYZE, TIMING OFF) SELECT m.\"Id\" FROM \"Mails\" m WHERE m.\"FolderPath\"='INBOX' AND NOT m.\"IsDraft\" AND ($2) ORDER BY m.\"SentDate\" DESC LIMIT 51"
  for i in 1 2 3; do docker exec postgres-pgvector psql -U postgres -d srch_lab -Atc "$sql" >/dev/null; done
  local times=$(for i in $(seq $N); do docker exec postgres-pgvector psql -U postgres -d srch_lab -Atc "$sql" | sed -n 's/^Execution Time: \([0-9.]*\) ms/\1/p'; done | sort -n)
  local p50=$(echo "$times" | sed -n "$((N/2))p"); local p95=$(echo "$times" | sed -n "$((N*95/100))p")
  local rows=$(docker exec postgres-pgvector psql -U postgres -d srch_lab -Atc "SELECT count(*) FROM (${sql#EXPLAIN (ANALYZE, TIMING OFF) }) x")
  printf '%-58s rés.=%-3s p50=%7s ms  p95=%7s ms\n' "$1" "$rows" "$p50" "$p95"
}
W="' ' || regexp_replace(search_normalize(coalesce(m.\"FromName\",'') || ' ' || m.\"FromAddress\"), '[^[:alnum:]]+', ' ', 'g')"
S="' ' || regexp_replace(search_normalize(coalesce(m.\"Subject\",'')), '[^[:alnum:]]+', ' ', 'g')"
R="EXISTS (SELECT 1 FROM \"MailRecipients\" r WHERE r.\"MailId\"=m.\"Id\" AND ' ' || regexp_replace(search_normalize(coalesce(r.\"Name\",'') || ' ' || r.\"Address\"), '[^[:alnum:]]+', ' ', 'g') LIKE '% '||search_normalize('dupont')||'%'"
if [ -z "$ONLY_PREFILTER" ]; then
echo "== De : mot fréquent (virginie) puis rare (cerballiance)"
run "avant  De virginie (ILIKE adresse ou nom)" "m.\"FromAddress\" ILIKE '%virginie%' OR m.\"FromName\" ILIKE '%virginie%'"
run "après  De virginie (mots normalisés)" "$W LIKE '% '||search_normalize('virginie')||'%'"
run "avant  De cerballiance" "m.\"FromAddress\" ILIKE '%cerballiance%' OR m.\"FromName\" ILIKE '%cerballiance%'"
run "après  De cerballiance" "$W LIKE '% '||search_normalize('cerballiance')||'%'"
run "après  De cyril toubib (deux mots)" "$W LIKE '% '||search_normalize('cyril')||'%' AND $W LIKE '% '||search_normalize('toubib')||'%'"
echo "== Objet : fréquent (compte) puis rare (xyzabs)"
run "avant  Objet compte (ILIKE)" "m.\"Subject\" ILIKE '%compte%'"
run "après  Objet compte" "$S LIKE '% '||search_normalize('compte')||'%'"
run "avant  Objet xyzabs" "m.\"Subject\" ILIKE '%xyzabs%'"
run "après  Objet xyzabs" "$S LIKE '% '||search_normalize('xyzabs')||'%'"
echo "== À : rare (dupont)"
run "avant  À dupont (ILIKE)" "EXISTS (SELECT 1 FROM \"MailRecipients\" r WHERE r.\"MailId\"=m.\"Id\" AND (r.\"Address\" ILIKE '%dupont%' OR r.\"Name\" ILIKE '%dupont%'))"
run "après  À dupont" "$R)"
fi
if [ -z "$ONLY_SPLIT" ]; then
echo "== Avec préfiltre SearchText (index trigramme), chaque mot"
P() { echo "m.\"SearchText\" LIKE '%'||search_normalize('$1')||'%'"; }
run "préfiltre  De virginie" "$(P virginie) AND $W LIKE '% '||search_normalize('virginie')||'%'"
run "préfiltre  De cerballiance" "$(P cerballiance) AND $W LIKE '% '||search_normalize('cerballiance')||'%'"
run "préfiltre  De cyril toubib" "$(P cyril) AND $(P toubib) AND $W LIKE '% '||search_normalize('cyril')||'%' AND $W LIKE '% '||search_normalize('toubib')||'%'"
run "préfiltre  Objet compte" "$(P compte) AND $S LIKE '% '||search_normalize('compte')||'%'"
run "préfiltre  Objet xyzabs" "$(P xyzabs) AND $S LIKE '% '||search_normalize('xyzabs')||'%'"
run "préfiltre  Objet cr (2 lettres)" "$(P cr) AND $S LIKE '% '||search_normalize('cr')||'%'"
run "sans       Objet cr (2 lettres)" "$S LIKE '% '||search_normalize('cr')||'%'"
fi
if [ -n "$ONLY_SPLIT" ]; then
N1="search_normalize(coalesce(m.\"FromName\",'') || ' ' || m.\"FromAddress\")"
run "normalisé seul  De cerballiance" "$N1 LIKE '%'||search_normalize('cerballiance')||'%'"
run "normalisé + mots  De cerballiance" "$N1 LIKE '%'||search_normalize('cerballiance')||'%' AND $W LIKE '% '||search_normalize('cerballiance')||'%'"
run "lower seul  De cerballiance" "lower(coalesce(m.\"FromName\",'') || ' ' || m.\"FromAddress\") LIKE '%cerballiance%'"
fi
