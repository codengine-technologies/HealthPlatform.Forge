# task-423 — /review : CHANGES REQUESTED (règle 1b)

**Étape** : `/review`, verrou « test d'intégration » (step 4a). **Nature** : comportements atteignables par un
endpoint, modifiés par la task, sans test d'intégration qui les prouve. Aucune PR ouverte, task laissée en `wip-*`.

## Ce qui est vert

- Build et tests de `api-mail` sur `feat/task-423-…` @ `0e2c5172` : domain 202, infrastructure 700, application 4 003,
  api 1 337, intégration 1 104 (+16 ignorés), 0 échec.
- `/sonar` : Quality Gate OK, new_coverage 96,1 %, 0 issue. `/e2e` : vert (58 + 71), parité verte.
- Comportements prouvés de bout en bout, vus rouges :

| Comportement | Test d'intégration | Preuve rouge |
|---|---|---|
| `GET /mail/folders`, base du praticien qui annule les requêtes → 503 `DATABASE_UNAVAILABLE` | `PractitionerDatabaseUnavailableEndToEndTests.ListingTheFolders_WhenThePractitionerBaseCancelsTheQuery_Returns503DatabaseUnavailable` | M1 (filtre retiré → 500) |
| Route qui exige une boîte, registre injoignable, compte en cache → 503, jamais 403 | `RegistryUnavailableEndpointIntegrationTests.MailboxRoute_WhenTheRegistryIsUnavailable_Answers503_NeverMailboxNotAttached` | M2 (dégradation remise sur `GetMailboxAsync` → 403) |
| Idem, cache froid | `…_AndTheAccountIsNotCached_Answers503` | M3 (dégradation remise sur `GetAccountAsync` → 403) |
| Route `[MailboxNotRequired]`, registre injoignable → servie sans boîte | `MailboxOptionalRoute_WhenTheRegistryIsUnavailable_IsServedWithoutAMailbox` | mutation faite en revue : filtre du middleware inversé → 503 au lieu de 200 |

## Ce qui bloque

Le diff pose le filtre `when (!DatabaseAvailability.IsUnavailable(ex))` sur trois autres chemins. Chacun change la
réponse d'un endpoint (500 → 503), et **aucun test d'intégration ne le lit** :

| Endpoint | `catch` modifié | Mesuré au banc (palier 1400) |
|---|---|---|
| `GET /api/v1/mail/folders/{folder}` | `ImapService.ReadFolderAsync` | **3 841 × 500**, le cas dominant |
| `GET /api/v1/mail/folders/{folder}/emails/today` | `ImapService.ReadTodayAsync` | 108 × 500 |
| `GET /api/v1/mail/folders/{folder}/emails/content/{uid}` | `ImapService.GetEmailContentInternalAsync` (lecture du message) | 135 × 500 |

Règle 1b : « au moins un test d'intégration par endpoint » est un plancher, pas le critère. Chaque comportement
modifié doit être lu dans la réponse réelle et vu rouge. La DOD ne cite que `GET /mail/folders`, mais la règle
s'applique au diff.

## Ce qu'il faut faire (reprise par `/develop task-423`, puis la chaîne)

Dans `PractitionerDatabaseUnavailableEndToEndTests`, avec le même harnais (`ArchiveMailboxServer`,
`PractitionerBaseSaturation`), un test par endpoint ci-dessus :
- 503, `application/problem+json`, `code` = `DATABASE_UNAVAILABLE`, `detail` fixe ;
- avec un message déposé au préalable, pour `today` et `content` ;
- en verrouillant les tables que chaque chemin lit sous le `catch` filtré (vraisemblablement `Mails`, pas seulement
  `MailFolders`) ;
- vu rouge par mutation du filtre correspondant.

Aucune décision humaine n'est nécessaire : c'est un complément de preuve, le code de production ne change pas a priori.

## Suggestion non bloquante (pour l'humain)

Le 503 `TENANT_REGISTRY_UNAVAILABLE` rend en `detail` le message de l'exception typée : « Le registre est injoignable.
Opération=GetAccountAsync CorrelationId=… ». Ni donnée de santé ni message système brut, mais un libellé technique.
Il sort désormais à chaque requête pendant une panne du registre. Blazor (`ProblemDetailsParser`) et la recherche
mobile affichent `detail`. Un `detail` fixe pour l'indisponible du registre, comme pour `DATABASE_UNAVAILABLE`,
serait plus juste. Hors DOD de task-423 : à trancher par l'humain (complément de cette task, ou task à part).

---

# 2ᵉ passage de `/review` (après la reprise, `fccd6fc2`) : CHANGES REQUESTED, un comportement non prouvé

Le premier blocage est levé : les trois routes ont été retirées du périmètre par décision humaine (leurs 500 sont des
pannes IMAP, task-425), et le libellé fixe du 503 du registre est prouvé.

**Reste un comportement modifié, atteignable par un endpoint, sans test d'intégration** (règle 1b) : les routes de
gestion des boîtes. `MailboxManagementService` (et `MailboxSenderIdentityService.CanEditAsync`) appellent
`GetAccountAsync` / `ListMailboxesAsync` / `GetMailboxAsync`, qui ne dégradent plus. Pendant une panne du registre,
`GET /api/v1/account/mailboxes` passe donc de **200 avec une liste vide** (« aucune boîte rattachée », ce qui invitait
le médecin à rattacher de nouveau la sienne) à **503 `TENANT_REGISTRY_UNAVAILABLE`**. C'est voulu et écrit dans le
`## Develop log`, mais aucun test ne le lit.

**Ce qu'il faut faire (`/develop task-423`)** : dans `MailboxAttachRoleIntegrationTests` (vrai `AccountController`,
vrai `MailboxManagementService`, vrai registre PostgreSQL), un test qui coupe la base du registre
(`ALLOW_CONNECTIONS false`, comme `RegistryUnavailableEndpointIntegrationTests`) puis lit
`GET /api/v1/account/mailboxes` : 503, `code` = `TENANT_REGISTRY_UNAVAILABLE`, `detail` fixe, jamais `200 []`.
Vu rouge en remettant la dégradation de `ListMailboxesAsync` (et de `GetAccountAsync`) : 200 et une liste vide.
Aucune décision humaine nécessaire.
