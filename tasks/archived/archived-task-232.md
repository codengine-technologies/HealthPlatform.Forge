# task-232 — Des messages enrichis sont servis par IMAP au prix du froid : réconcilier l'asymétrie d'UidValidity entre lecture et enrichissement, et rendre la mesure discriminante — ANNULÉE

> ## 🚫 US ANNULÉE le 2026-08-05 — décision humaine
>
> Abandonnée à la demande de l'humain, **après la Phase 1**. Le corps de la US est conservé
> tel quel ci-dessous : il documente une hypothèse sérieuse et les mesures qui l'ont mise en
> doute, et cela vaut d'être relisible.
>
> ### Où en était le travail
>
> **Phase 1 était livrée et poussée** — commit **`3fd1dac`** sur
> `fix/task-232-uidvalidity-lecture-enrichissement` (`api-mail`). Aucune PR n'a été ouverte.
>
> Elle contenait le témoin `mssante_mail_content_served_total` (étiquette `served_from` ∈
> {`db`, `imap`}), posé aux deux côtés du point de décision de
> `ImapService.GetEmailContentInternalAsync`, avec 7 tests et une preuve ROUGE.
>
> **Phase 2 n'a jamais été entamée**, sur ordre de la US elle-même : le désalignement
> d'`UidValidity` mesuré était **nul** (51 messages sur 51 alignés sur la génération de leur
> dossier, aucune ligne à `UidValidity = 0`), donc la fenêtre de dérive décrite ne s'était pas
> produite. Cette mesure n'infirmait pas l'hypothèse — base de développement et non base du
> banc, un seul dossier peuplé, une seule génération — mais elle ne la soutenait pas.
>
> ### ⚠️ Ce que cette annulation abandonne, et qu'il faudra refaire
>
> Le témoin `served_from` **n'est pas sur `develop`**. Il vit dans le commit `3fd1dac`, sur une
> branche sans PR. Conséquence concrète : **rien ne permet aujourd'hui de dire si une ouverture
> de message chaude est servie par la base ou par le serveur.** L'étape 3 du parcours du banc
> reste donc mesurée à 407 ms p50 pour un message déjà en base, avec une moyenne (327 ms) sous
> sa médiane — signature d'un mélange que personne ne peut ventiler.
>
> Le commit est conservé et récupérable par `git cherry-pick 3fd1dac` : la branche **locale**
> n'est pas supprimée. Si le sujet revient, ne pas réécrire l'instrument — le reprendre.
>
> ### Une piste à ne pas perdre, indépendante de l'UidValidity
>
> Si l'étape 3 reste lente alors que le contenu vient bien de la base, le suspect n'est pas le
> choix de la source mais **`htmlBodySanitizer.Sanitize`** : l'assainissement AngleSharp posé
> par task-088 tourne **sur le chemin chaud, à chaque ouverture, sur tout le corps HTML**. La
> US ne l'envisageait pas. C'était détaillé dans `questions/task-232.md`, conservé.
>
> ### Ce qui a été produit et qui SURVIT à cette annulation
>
> Une correction de documentation sans rapport avec l'hypothèse de cette US, faite en mesurant
> pour elle : la preuve invoquée par **task-233** contre `MailFolders.FolderType` était un
> **état transitoire** (`Trash` est correctement classé après resynchronisation). Corrigée dans
> `E015-Changelogs.md` (v1.27), `E015-tests-charge-api-mail.md` (v1.28) et
> `archived-task-233.md` — commit `bffe728`. **Cette correction reste valide.**
>
> ### Branches
>
> - `api-mail` : remote supprimé, **branche locale conservée** (elle porte `3fd1dac`)
> - `dtos-mss` : branche auto-incluse restée **vide** — supprimée en local et sur le remote


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


## Branches

- `api-mail` (pushed) : `fix/task-232-uidvalidity-lecture-enrichissement` —
  https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-232-uidvalidity-lecture-enrichissement
- `dtos-mss` (pushed) : `fix/task-232-uidvalidity-lecture-enrichissement` — **auto-incluse**
  par `/start` (règle CLAUDE.md). Aucun changement de contrat n'est attendu : si elle reste
  vide, **aucune PR ne sera ouverte pour elle**.

> ⚠️ **Rappel du défaut de cycle**, qui vient de bloquer `/start` deux fois de suite : rien
> dans la chaîne ne nettoie une branche auto-incluse restée **vide**. Si `dtos-mss` ne reçoit
> aucun commit, il faudra la supprimer à la main au merge — comme cela a été fait pour
> task-233.

Pré-flight : les six repos automatisés mesurables étaient sur `develop`
(`api-mail`, `client-blazor`, `client-mobile`, `dtos-mss`, `sdk`, `interop-cda`).
`host` n'est pas un dépôt git — non mesurable, cf. l'avertissement de CLAUDE.md.
Dépendances vérifiées archivées : task-224, task-225.
