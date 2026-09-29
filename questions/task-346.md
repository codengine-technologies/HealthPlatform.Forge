# task-346 — /review CHANGES REQUESTED (2026-09-29)

Validation : build + tests verts (api-mail 5 849/5 849 ; Angular build + test 11 projets). Revue
indépendante : **5 bloquants**.

1. **DRAFT-001** — après rechargement, `mailRow(subject).toBeHidden()` passe pendant le spinner de
   la liste (Brouillons vide) : un « supprimer » sans effet serveur resterait vert. Attendre la fin
   du chargement (`.mail-list-loading` masqué ou `.mail-list-empty` visible) avant d'asserter.
2. **SIGNATURE-001** — les deux « disparue » peuvent passer pendant `loadSignatures()`
   (`isLoading`), et l'ancre post-rechargement `.sig-list-content` est rendue pendant le chargement.
   Attendre `.sig-empty` (le seed n'a aucune signature) avant `toHaveCount(0)`.
3. **`run.mjs`** — un `session.env` laissé par un arrêt sur signal de l'orchestrateur mobile est lu
   au run suivant avant que l'enfant ne vide `out/` : mauvaise clé, backend pas prêt, faux rouge
   (code 1 au lieu de 2). Supprimer `session.env` et `STOP` avant le spawn.
4. **INBOX-001** — l'ouverture de la recherche est réduite à `toBeVisible()` du champ, et les écarts
   weda2 (« Lus » au lieu de « Signalés », vue conversation dans les Paramètres) ne sont consignés
   que dans le README, pas dans `scenarios.yml`. Ouvrir la recherche (`mail-search-dropdown`) et
   porter les écarts dans le catalogue.
5. **DETAIL-002** — aucun contrôle qu'un corps s'affiche : un rendu HTML vide passerait. Asserter le
   corps HTML visible et non vide avant la première bascule et après la seconde.

Suggestions : restaurer les réglages de SETTINGS-001/002 en `finally` ; SEARCH-001 attend la
requête plutôt que `mail-search-clear` ; code 2 si Playwright ne produit aucun rapport ; README :
`npm ci` du mobile requis (le backend sert aussi l'app mobile) ; retries sans effet sur les tests
qui mutent l'état seedé (documenté).
