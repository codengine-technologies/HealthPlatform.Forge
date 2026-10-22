# task-386 — `/review` : CHANGES REQUESTED — **résolu le 2026-10-23** (seconde revue APPROVED, PR api-mail #305, mobile #99, blazor #95)

**Date** : 2026-10-23 · **Étape** : `/review` (après `/develop` → `/sonar` → `/lint-angular` → `/lint-mobile` → `/e2e`, tous verts)
**État** : la task reste en `wip-task-386.md` ; aucune PR ouverte. Branches poussées : api-mail et client-mobile
`fix/task-386-annuaire-recherche-fiable` ; client-angular : modifications non commitées (code seul).

## Ce qui est validé

- Build et tests : api-mail ✓ (domain 195, infrastructure 695, application 3 599, api 1 276, intégration 946/949 —
  voir « Flaky de minuit » plus bas) ; client-mobile ✓ (build, 1 154 tests) ; weda2 ✓ (`libs/mss` 991 tests,
  affected 12 projets).
- Sonar : Quality Gate OK, nouveau code à 0 finding, couverture du nouveau code 97,1 %.
- E2E : vert, parité verte (mobile 39, Angular 46 + 1 flaky préexistant).
- Règle 1b : chaque comportement de la route est prouvé par un test d'intégration de bout en bout **et** vu rouge
  (10 mutations : M1 à M10, voir `## Develop log` ; M9 « nom court accepté » et M10 « en-tête absent » jouées en
  `/review`, rouges).

## Bloquants (à corriger, puis relancer la chaîne depuis `/develop task-386`)

1. **Une recherche incomplète sans résultat s'affiche « Aucun praticien trouvé » (weda2 et mobile).**
   `dirNoMatch` (`mss-contacts.component.ts`, `contacts.page.ts`) ne regarde que `dirError === null` et une liste
   vide. Quand l'annuaire a répondu à la première page puis a refusé ou dépassé l'échéance (ou a refusé tous les
   appels pour quota), l'écran affiche en même temps « Recherche incomplète » et « Aucun praticien trouvé —
   vérifiez l'orthographe ». C'est le défaut que la task devait supprimer.
   *Correctif* : `dirNoMatch` exige aussi une recherche complète (`dirIncompleteMessage() === null`), dans les deux
   clients ; un test de composant « incomplète et vide : pas d'« aucun praticien » » dans chacun.

2. **Une virgule dans un critère contourne la règle des 3 caractères.**
   La passerelle lit `%2C` comme un OU FHIR (vérifié pour `_id`, vrai pour tout paramètre). `LastName=dup,a`
   envoie `family=dup OR a` : la validation compte 5 caractères, la recherche porte sur « a ». Idem pour le prénom
   et le nom d'organisation.
   *Correctif* : refuser (400) ou neutraliser `,` `|` `$` `\` dans les champs texte (`NormalizeQuery` ou
   `AnnuaireQuery.Where`), test de route « nom avec virgule → 400, aucun appel ».

3. **Le cas de référence (« dup » + « 18 ») n'est pas prouvé sous l'échéance de 10 s avec la latence réelle.**
   29 appels, tous séquentiels. Les mesures du 2026-10-22 (`Docs/annuaire-sante-fhir-api.md`) donnent ~10,7 s de
   latence réelle pour ce parcours (17,7 s moins 7 s d'espacement de test) : la recherche canonique risque de
   rendre `incomplete;reason=deadline`. Les tests, à horloge simulée, ne peuvent pas le voir.
   *À faire* : mesurer la recherche réelle une fois (≈ 30 appels, hors CI). Si elle dépasse, deux leviers au choix :
   lots d'établissements en parallélisme borné (2 à 3 ; la porte de budget tient déjà le quota), ou échéance portée
   à 15 s.

## Réponses de l'humain (2026-10-23)

1. **503** dès qu'aucun appel n'a abouti, 429 compris.
2. **client-blazor inclus maintenant** dans task-386 (branche créée, `**Repos**` mis à jour).
3. **Spécialité + organisation sans lieu : gardée. Organisation seule : au moins 3 caractères.**

→ DoD mise à jour dans `tasks/wip-task-386.md` ; relance de la chaîne depuis `/develop task-386`.

## Décisions demandées à l'humain (tranchées ci-dessus)

4. **429 sur tous les appels : 200 vide + `incomplete;reason=quota`, ou 503 ?** Le code suit la DoD (« 429
   persistant : 200 avec les résultats obtenus, issue `incomplete;reason=quota` »). La relecture fait valoir qu'avec
   zéro réponse, client-blazor (qui ne lit que le corps) affiche de nouveau « 0 praticien ». Option : 503
   `DIRECTORY_UNAVAILABLE` dès qu'aucun appel n'a abouti, quelle qu'en soit la cause.
5. **client-blazor hors périmètre** : il accepte encore un nom de 2 caractères (désormais 400, avalé en liste vide)
   et ignore l'en-tête d'issue. Proposer une task de suite ?
6. **Spécialité + organisation sans lieu** est acceptée (la DoD ne parle que de « spécialité sans lieu ») ;
   **organisation seule de 2 caractères** (« CH ») acceptée. Garder, ou exiger davantage ?

## Suggestions (à traiter dans la relance ou en suite)

- **Repli Redis** (`RedisAnnuaireQuotaGate`) : chaque instance retombe sur 15/s (5 instances → 75/s contre 17) et
  journalise un avertissement par appel ; un Redis lent coûte le délai StackExchange à chaque appel. Repli à
  `RequestsPerSecond / instances`, coupe-circuit court, avertissement unique.
- **RPPS à 12 chiffres** (IDNPS « 8 » + RPPS) : `SanitizeInput` tronque à 11 avant le contrôle (code antérieur).

## Flaky de minuit (préexistant, hors task)

3 tests d'intégration « messages du jour » IMAP (`EmailReadingUseCaseTests.FilterTodayEmails…`,
`ImapFolderServiceIntegrationTests.GetFolder(NotSeen)TodayAsync…`) ont échoué au run de validation lancé à
00:03 heure locale (22:03 UTC) : le seed et le filtre « aujourd'hui » ne sont pas sur le même jour entre minuit
local et minuit UTC. Fichiers hors du diff ; verts aux quatre runs complets de la soirée. À traiter dans une task
dédiée (date de référence injectée plutôt que l'horloge système).
