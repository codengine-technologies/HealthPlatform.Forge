# task-449 — /review passage 4 : CHANGES REQUESTED, après la reprise 3

**Étape** : `/review`, 4ᵉ passe (revue indépendante, 2026-11-12), après la reprise 3 demandée par l'humain. Build, tests
(api-mail 7 948, mss-lib 1 647, weda2 2 683), Sonar (QG OK, 0 issue nouveau code) et `/e2e` (mobile 61, angular 84,
parité verte) sont verts. B4, B5, S16, S17, et les arbitrages S4/S5 et S7, sont livrés et prouvés rouges. La PR n'est
**pas** ouverte. La task reste en `wip-*` (`**Reprises**: 3`).

## Bloquants (passe 4) — corrigeables par la forge

### B1 — Un critère « Objet » / « De » / « À » avec une apostrophe courbe ne trouve plus rien

- Le motif tapé est normalisé par le jumeau C# (`SearchTerms.Normalize`), la colonne par `search_normalize` (SQL).
  `unaccent` réécrit la ponctuation typographique (`’` → `'`), le jumeau non. Vérifié en base :
  `unaccent('Compte rendu d’échographie')` = `Compte rendu d'echographie`.
- Scénario : objet copié depuis un mail Outlook (« Compte rendu d’échographie ») collé dans « Objet » : 0 résultat.
  L'ancien `ILIKE` le trouvait. Régression introduite par l'alignement S4/S5.
- Correctif : normaliser le motif par la même fonction SQL que la colonne. Test d'intégration avec `’`, vu rouge.

### B2 — Un Ctrl+clic (macOS) sur un patient suggéré ouvre son dossier

- Le choix se fait au `mousedown` et ne filtre que `button !== 0`. Sur macOS, Ctrl+clic (menu contextuel) arrive avec
  `button === 0` : la vue « Mails du patient » s'ouvre, consultation tracée. Appuyer puis glisser hors de l'entrée
  choisit aussi.
- Correctif : choisir au `click`, sans touche de modification ; garder `preventDefault()` au `mousedown`. Tests vus
  rouges.

## Suggestions (même reprise)

- **S3** — à la fermeture, la requête en vol n'est annulée qu'après 250 ms (le `''` traverse le `debounceTime`).
- **S4** — `de : "" martin` : une paire de guillemets vide ne coupe pas le préfixe (critère `"" martin`, 0 résultat).
- **S2** — mesurer « De » / « Objet » normalisés sur la boîte de 11 178 messages (calcul de `search_normalize` ligne à
  ligne) ; préfiltre par l'index trigramme de `SearchText` si besoin.

## Arbitrage humain

- **S1** — les critères tapés cherchent une sous-chaîne contiguë, les suggestions chaque mot en début de mot dans
  n'importe quel ordre : `de : martin helene` propose « Hélène Martin », mais Entrée sans choisir rend 0 résultat (idem
  `jean pierre` / « Jean-Pierre »). **Recommandation forge : aligner aussi l'ordre des mots et la ponctuation** (chaque
  mot tapé doit figurer en début de mot), puisque la barre promet de chercher « comme les suggestions ». Sinon : laisser
  tel quel (sous-chaîne), le médecin choisit dans la liste.
  **Tranché par l'humain le 2026-11-12** : un critère tapé sans guillemets cherche **chaque mot, dans n'importe quel ordre**, comme les suggestions (`de : martin helene` trouve « Hélène Martin ») ; entre guillemets (`de : "Hélène Martin"`), les mots se cherchent **dans l'ordre strict**, d'un seul tenant. Lecture forge, inchangée par cet arbitrage : accents et casse restent ignorés dans les deux cas (S4/S5).

## Pourquoi la chaîne s'arrête

Trois reprises faites (plafond de la règle 13 : 2 ; la 3ᵉ demandée par l'humain). B2 est de la même famille que B5
(un choix de patient sans geste délibéré). Les deux bloquants sont petits et localisés : la forge recommande une 4ᵉ
reprise (`relance`), avec S1 tranché d'abord.

## Reprise

`/develop task-449 --reprise` corrige B1, B2, S2, S3, S4 (chaque correctif vu rouge), et S1 selon l'arbitrage, puis la
chaîne reprend jusqu'à `/review`.
