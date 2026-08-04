# todo-task-232.md — Des messages enrichis sont servis par IMAP au prix du froid : réconcilier l'asymétrie d'UidValidity entre lecture et enrichissement, et rendre la mesure discriminante

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: task-224 (archivée) — a corrigé le défaut « l'étape 3 mesurait
du froid » côté harnais ; cette task instruit le pendant **serveur** du même
symptôme. task-225 (archivée) — a posé le compteur de sollicitations que cette
task rend discriminant.
**Priorité**: **2** — `read_content` est hors grille SLO (p50 407 ms pour un
message **déjà en base**) et pèse 9,8 % du temps serveur. Particularité : la
cause est **cernée mais pas encore prouvée par la mesure** — cette task
commence par la prouver, conformément à la discipline de l'EPIC (task-222).

> ⚠️ **Contrainte absolue — aucun impact frontend.** Même route
> (`GET Mail/folders/{foldername}/emails/content/{emailid}`), même DTO
> `MailContentDto`, même sémantique. Les correctifs sont : cohérence interne
> base/IMAP + télémétrie.

## Objective

Qu'un message dont le contenu est déjà en base soit **effectivement** servi
par la base (~quelques ms), et non par un repli IMAP à 4-6 commandes sous le
verrou de session (~400 ms). L'analyse de code a établi :

1. **Le branchement « servi base » existe et est correct**
   (`ImapService.GetEmailContentInternalAsync` : retour immédiat sans IMAP ni
   verrou si la ligne `Mails` + `MailContents` est trouvée). `MailContents`
   couvre tous les champs de `MailContentDto` — rien ne manque en base.
2. **Mais la télémétrie du tir est bimodale** : une fraction des ouvertures
   « chaudes » sort en quelques ms (la même route sort à 3,8 ms p50 sous le
   tag `patient_docs`), la **majorité coûte exactement le prix du froid**
   (p50 407 ms ≈ 427 ms du chemin froid ; moyenne < p50, signature d'un
   mélange).
3. **Candidat n°1, documenté mot pour mot dans le code du repo**
   (commentaire dans `MailRepository`) : l'**asymétrie d'`UidValidity`** —
   la lecture filtre sur `Mails.UidValidity == MailFolders.UidValidity`,
   tandis que les tests « déjà enrichi » côté écriture (`GetEnrichedUidsAsync`,
   `TryResolveExistingMailAsync`) **ignorent la génération**. Une ligne à
   génération périmée est donc invisible en lecture (→ IMAP à chaque
   ouverture) **et** comptée comme enrichie (→ jamais réanalysée) : le pire
   des deux mondes, indéfiniment.
4. **Le mécanisme de dérive existe** : l'upsert de dossier (appelé en
   permanence par `GET mail/folders`) peut faire passer l'`UidValidity` du
   dossier de 0 à la valeur serveur **sans estampiller les mails** ;
   l'estampillage (`SyncUidValidityAsync`, branche `Adopted`) exige
   `UidValidity == 0` à ce moment précis.
5. **La mesure actuelle ne peut pas trancher** : le compteur task-225 et
   l'étiquette de verrou agrègent sous `GetEmailContent` trois opérations k6
   différentes (`read_content`, `read_content_cold`, `patient_docs`) — aucun
   témoin ne distingue « servi base » de « servi IMAP » sur cette route.

## Déroulé exigé — mesurer d'abord, corriger ensuite

**Phase 1 — rendre la mesure discriminante et prouver la cause** :
- ajouter au compteur de sollicitations (task-225) une dimension
  `served_from = db | imap` sur la route contenu (et l'exposer dans le
  rapport du banc si trivial côté `report.py` — sinon relevé Prometheus
  manuel) ;
- vérifier en base du banc l'ampleur du désalignement :
  `Mails.UidValidity` vs `MailFolders.UidValidity` par dossier, et le compte
  de `Mails` enrichis invisibles en lecture ;
- si la cause n'est **pas** l'UidValidity (part `served_from=imap` faible ou
  désalignement nul), **s'arrêter et ouvrir `questions/task-232.md`** avec
  les mesures — ne pas corriger à l'aveugle.

**Phase 2 — corriger l'asymétrie (si la Phase 1 la confirme)** :
- aligner les tests « déjà enrichi » côté écriture sur le même filtre de
  génération que la lecture (un mail à génération périmée redevient candidat
  à l'enrichissement, donc redevient servable) ;
- estampiller les mails lors de l'adoption d'une `UidValidity` par le dossier
  quand le contenu est toujours valide (le cas nominal Dovecot : la
  génération ne change pas, seul le 0 initial est adopté) — ou réanalyser,
  au choix documenté par la mesure ;
- corriger au passage le commentaire faux du harnais (`journey.js:374-378` :
  le chemin de lecture IMAP ne décode **pas** le CDA à la volée — une
  ouverture non analysée renvoie `medicalDocuments: []`).

## La mesure — tirs `journey-mssante-n300` du 2026-08-04

| Signal | Valeur (tir 17:05) |
|---|---|
| `read_content` (servi base) p50 / p95 | 407 / 588 ms — hors grille, quasi égal au froid (427 / 605 ms) |
| Part du temps serveur | 9,8 % (3 292 s, 9 658 appels) |
| Même route sous `patient_docs` (servi base avéré) | **3,8 ms p50** — borne le coût du chemin sans IMAP |
| `read_content` moyenne < p50 (327 < 407) | signature d'un mélange bimodal : une masse quasi nulle + une masse au prix du froid |

## Definition of Done

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] **Zéro changement de contrat** : route, DTO, sémantique inchangés — tests d'intégration existants inchangés
- [ ] Dimension `served_from` (db/imap) posée sur la télémétrie de la route contenu — unit test
- [ ] Phase 1 documentée dans la task : part mesurée de `served_from=imap` sur la bande analysée + requêtes SQL de désalignement et leurs résultats
- [ ] Si cause confirmée : tests « déjà enrichi » côté écriture alignés sur le filtre de génération de la lecture — unit tests (mail à génération périmée : redevient candidat à l'enrichissement ET n'est plus compté enrichi)
- [ ] Si cause confirmée : adoption d'`UidValidity` par le dossier n'orpheline plus les mails enrichis — unit test du scénario « dossier 0 → valeur serveur avec mails existants »
- [ ] Aucun message enrichi deux fois avec des contenus divergents (idempotence de la réanalyse) — test
- [ ] Aucune donnée de santé en clair dans les logs ni dans les étiquettes de télémétrie (dimension `served_from` = valeur technique, jamais de contenu)
- [ ] **Contre-épreuve au banc (bloquante pour le merge, pas pour la PR)** : tir `journey` n300 iso-conditions avant/après :
  - `read_content` (étape 3) p50 **très nettement réduit** vers le coût base (référence : 407 ms ; borne connue du chemin base : ~4 ms + sérialisation)
  - part `served_from=db` sur la bande analysée proche de 100 %
  - vérification par base toujours PASS (complétude 98/98 tenue — la réanalyse éventuelle ne casse rien)

## Manual Test Plan

- Monter le banc : skill `loadtest-skill`
- Phase 1 : relever `mssante_mail_server_solicitations_total` ventilé par
  `served_from` pendant un tir court (n10 suffit), et exécuter les requêtes
  SQL de désalignement sur la base du banc :
  - `SELECT m."UidValidity", count(*) FROM "Mails" m WHERE m."FolderPath"='INBOX' GROUP BY 1;`
  - `SELECT "Path","UidValidity" FROM "MailFolders";`
  - compte des `Mails` enrichis dont la génération diffère de celle du dossier
- Phase 2 : tir de contre-épreuve `journey` n300 iso-conditions avec
  `journey-mssante-n300-170512`, comparer l'étape 3 et la ventilation
  `served_from`
- Contrôle fonctionnel : ouvrir un message analysé → contenu + documents
  médicaux identiques à avant (mêmes données, juste plus vite)

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — correctif de cohérence interne + télémétrie
- **Exigences DSR honorées** : non applicable — pas de changement fonctionnel
- **INS** : non applicable — le rattachement INS des documents est inchangé ; une réanalyse éventuelle repasse par le pipeline existant (identito-vigilance intacte : jamais de rattachement deviné)
- **Authentification PS** : inchangée
- **Habilitations** : non applicable — cloisonnement par boîte praticien inchangé
- **Interop CI-SIS** : non applicable — le parsing CDA n'est pas modifié ; s'il y a réanalyse, c'est le pipeline `interop-cda` existant qui tourne
- **Tracé PGSSI-S** : inchangé — la consultation d'un message reste tracée à l'identique
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — aucune donnée nouvelle stockée ; la dimension de télémétrie est purement technique
- **AIPD / impact RGPD** : inchangé
