# todo-task-323.md — Le HTML des documents médicaux ne voyage plus avec les listes : chargé à l'ouverture, sur les trois clients

**Repos**: api-mail, client-mobile, client-blazor
**Dependencies**: — (task-322 est mergée le 2026-09-20 ; cette US en est la seconde moitié)
**Epic**: E011
**Priorité**: **1** — **82 % du temps SQL restant** du parcours praticien mesuré au banc (tir A/B `terrain` 1 000 inscrits du 2026-09-19 soir, `Docs/audits/api-mail-loadtest-terrain-1000-task322-ab-20260919.md`) tient dans une seule requête : les documents médicaux de la page d'en-têtes, chargés **avec leur HTML** (222 Ko par document en moyenne). La cause est mesurée, l'attribution est faite par lecture du code des trois clients, et la seule dépendance réelle au HTML de liste est un écran mobile.

> **Origine.** task-322 a retiré des listes le contenu des pièces jointes et le
> vecteur d'embedding des documents, mais a **gardé `HtmlBody` et `Body`** des
> documents, au motif que Blazor et la frise patient mobile affichaient le document
> depuis la charge de la liste. La relecture faite le 2026-09-20 montre que cette
> dépendance est plus étroite que la PR #246 ne le disait : Blazor **recharge déjà**
> le contenu quand les documents d'un message n'ont ni corps ni HTML ; Angular
> recharge à l'ouverture ; le détail mobile passe par la route de contenu. **Seule la
> frise patient mobile** consomme le HTML depuis la liste. Cette US déplace ce
> chargement à l'ouverture du document, puis retire le HTML de la projection serveur.

## Ce qui est établi — tir A/B `terrain-1000-20260919-task322` (3 h, iso-conditions)

Sur **55,7 minutes de temps serveur SQL**, **45,7 vont à une requête**, émise par
`LoadBulkContentLookupsAsync` (`Api/Mail/src/Infrastructure/Repositories/MailDb/MailRepository.cs`, branche `headerOnly`, ~l. 1561) :

| Requête | Appels | ms / appel | Lignes / appel | Blocs / appel | Hors cache | Part du SQL |
|---|---|---|---|---|---|---|
| `SELECT m."Id", m."MailId", …, m."Body", m."HtmlBody", … FROM "MailMedicalDocuments" m WHERE m."MailId" = ANY($1)` (+ deux compteurs corrélés) | 28 228 | **97** | 17 | 640 | 15 % | **82,2 %** |

**Le plan n'est pas la cause** (0,5 ms mesurés par `explain` au tir du matin). **Le coût
est le volume détoasté** : `HtmlBody` fait 222 Ko en moyenne, soit ~3,8 Mo par page de
25 en-têtes, lus dans le TOAST (37 blocs par document, c'est le HTML découpé en morceaux
de 2 Ko). Ces 3,8 Mo traversent ensuite le réseau vers api-mail, sont matérialisés en
chaînes .NET (~7,6 Mo de tas géré par page, en Large Object Heap — la famille
d'allocations que task-194 a chiffrée), sérialisés en JSON, et **envoyés au client**
pour dessiner une liste qui ne les affiche pas.

**Appelants pendant le tir** : la page d'en-têtes `GET …/emails/{ids}` (~15,6 k appels)
et `GetMailAsync(Header)` derrière « marquer lu » (~12,4 k).

**Qui lit réellement le HTML depuis la liste** (relecture du 2026-09-20) :

| Client | Écran | Lit `BodyHtml` des documents de la liste ? | Comportement quand il est absent |
|---|---|---|---|
| Blazor | Boîte de réception | non — `LoadContent` (`MailListComponent.razor` ~l. 872) recharge par la route de contenu si tous les documents ont `Body` et `BodyHtml` vides | **déjà correct** |
| Blazor | Frise patient (`PatientTimeline.razor`) | non — lit `Category` et `DocumentDate` seulement | déjà correct |
| Angular | Frise patient, détail | non — recharge quand `content` est absent, et à l'ouverture | déjà correct |
| Mobile | Détail d'un message | non — route de contenu | déjà correct |
| **Mobile** | **Frise patient** (`patient-timeline.component.ts` ~l. 316, `timeline-document-group.component.html` ~l. 46, `medical-document-modal`) | **oui** — ne recharge que si `content` est nul ; l'aperçu déplié et la modale injectent `doc.bodyHtml` | **carte vide** si le serveur cesse d'envoyer le HTML |

**Ce qu'on ne sait pas encore** : la taille de la réponse HTTP de la page d'en-têtes
(non mesurée au banc, `data_received` k6 n'est pas tagué par opération) et la part des
45 ms de matérialisation de `GetMailsByUids` que ce HTML explique. Les deux se mesurent
dans le tir avant/après de cette US.

## Objective

Que le HTML et le corps d'un document médical **ne quittent la base que lorsque le
médecin regarde ce document** — ouverture d'un message, dépliage ou ouverture d'un
document dans la frise patient — et jamais pour dessiner une liste d'en-têtes ou une
frise repliée. Une ligne de liste ou une carte de frise a besoin de savoir qu'un
document existe (titre, date, catégorie, patient, praticien, PDF externe, marqueurs de
biologie et de synthèse) ; son HTML ne circule que sur les chemins de contenu, qui
existent déjà.

Ce que cette US change pour le médecin : la frise patient mobile ne télécharge plus
17 documents de 222 Ko à chaque page (le HTML arrive quand il déplie ou ouvre un
document) ; le serveur cesse de déplacer 3,8 Mo de données de santé par page d'en-têtes.
Ce qu'elle **ne change pas** : contenu affiché identique après ouverture, contrat
`MailMedicalDocumentDto` inchangé (les champs `Body` et `BodyHtml` restent, ils sont
**nuls sur les listes** et pleins sur les chemins de contenu), chemins `WithContent` et
route de contenu inchangés.

### Périmètre — dans l'ordre d'implémentation

L'ordre est choisi pour que le serveur ne change qu'une fois les clients tolérants aux
documents sans HTML. Les PRs s'ouvrent ensemble (une par repo) ; **l'ordre de merge est
`client-mobile` puis `client-blazor` puis `api-mail`** (encadré ci-dessous).

1. **Mobile, frise patient — charger le HTML à la demande, pas à la liste.**
   - `patient-timeline.component.ts` : supprimer `loadMailsContent` et ses deux appels
     (`loadFirstPage`, `loadMore`). La frise se construit à partir des métadonnées seules.
   - `timeline-document-group` : quand `toggleDocExpand` déplie un document dont
     `bodyHtml` et `body` sont vides, appeler la route de contenu du message
     (`getEmailContent(folderPath, uid)`), retrouver le document par `documentId` dans la
     réponse, recopier `bodyHtml`, `body`, `summaryItems` sur le document affiché. Un
     état de chargement par document (spinner). La branche « Aperçu indisponible — ouvrez
     le document » reste pour l'échec.
   - `medical-document-modal` : même mécanisme dans `ngOnChanges`, avec les inputs
     `folderPath` et `mailUid` qui existent déjà pour le PDF externe. Le HTML est chargé
     à l'ouverture de la modale, comme le PDF l'est aujourd'hui.
   - Un service `document-content.service.ts` (ou équivalent) factorise l'appel avec un
     cache par message, pour que la carte dépliée puis la modale ne fassent qu'**un**
     appel de contenu.
   - Le client mobile est **tolérant aux deux états** : documents avec HTML (serveur
     actuel) ou sans (serveur après cette US).
2. **Blazor — rien à coder, une preuve.** Un test bUnit fige le comportement de
   `LoadContent` : un `MailDto` dont les documents n'ont que des métadonnées déclenche le
   rechargement par la route de contenu, et le HTML s'affiche après. Vérifier au passage
   que `MailBodyComponent` (~l. 503) ne lit `BodyHtml` qu'après ce rechargement, et que
   `PatientTimeline.razor` ne lit ni `Body` ni `BodyHtml`.
3. **api-mail — retirer `Body` et `HtmlBody` de la projection d'en-tête.**
   - `LoadBulkContentLookupsAsync`, branche `headerOnly` (~l. 1580) : supprimer
     `Body = d.Body, HtmlBody = d.HtmlBody`. Le mapping vers `MailMedicalDocumentDto`
     (~l. 2323) recopie alors `null`. Remplacer le commentaire task-322 qui justifiait
     la conservation.
   - `MedicalDocumentTagListProjection` (~l. 1413) : vérifier l'alignement (déjà sans
     corps d'après `TagListingDoesNotReadAttachmentBytesNorDocumentBodies`).
   - `MailContents` en mode Header (~l. 1686) : confirmer par le test SQL que ni
     `BodyHtml` ni `Embedding` ne sont lus ; la forme n°15 du top 20 du tir B liste
     `Embedding` dans ses colonnes — identifier la requête émettrice (détail ou liste) et
     la corriger si c'est une liste.
   - Mode `WithContent` : inchangé, il lit les corps légitimement.
4. **api-mail — la forme n°4 du top 20, dans la même PR si l'attribution tient en une
   heure.** 67 770 appels, une ligne, 39 blocs, un document chargé entier (avec `Body`,
   donc `HtmlBody`). Ce n'est pas `ResolveActiveDuplicateRefsAsync` (projeté). Candidats :
   les deux `FirstOrDefaultAsync` par identifiant de `MailRepository` (~l. 2815, 2846),
   `BiologyAckRepository`. Attribuer par le journal SQL sur le parcours du banc, projeter
   l'appelant si son usage n'a pas besoin du HTML. Si l'attribution dépasse une heure,
   noter le finding dans le task file et le sortir de la PR : il ne retarde pas le point 3.
5. **Garde-fou d'ensemble** : dans `HeaderListingProjectionTests` (Testcontainers, SQL
   réellement exécuté) — la page d'en-têtes et « marquer lu » n'émettent aucun `SELECT`
   listant `"HtmlBody"` ou `"Body"` de `MailMedicalDocuments` ; le chemin `WithContent` et
   la route de contenu les listent toujours ; le test de caractérisation du DTO d'en-tête
   est mis à jour (`Body`/`BodyHtml` nuls sur les documents de la liste, tout le reste
   identique).

> **⚠️ Ordre de merge — arbitrage humain au HAG, pas pendant le cycle.** La PR
> `api-mail` ne doit être mergée et déployée **qu'après** la PR `client-mobile`
> (une frise mobile ancienne face au serveur nouveau afficherait des cartes vides).
> La PR Blazor est indépendante (test seul). `/review` le rappelle dans le body des
> trois PRs. Ce n'est pas un motif d'arrêt de la chaîne.

### Hors périmètre, explicitement

- **Le table splitting EF des colonnes blob** (`HtmlBody`, `Body`, `Content` portés par
  une entité séparée, chargée sur demande) : geste structurel qui rendrait tout `Include`
  correct par construction ; à instruire sur la mesure de cette US si un troisième blob
  apparaît.
- **Le regroupement des requêtes de la page** (14 requêtes SQL par appel de
  `GetMailsByUids`, 7 `DISCARD ALL` par requête HTTP) et le **cache du registre** (3
  lectures par requête) : US ultérieure.
- **La recherche textuelle `ILIKE`** (formes n°2 et 3, 7,4 % du SQL) et le **compteur par
  tag** (forme n°6) : findings distincts du même tir, à écrire séparément.
- Toute modification de `Dtos/`, `dtos-mss` ; `client-angular` (déjà correct, non listé).

### Mesure — avant / après, obligatoire

Tir `terrain` 1 000 inscrits en **iso-conditions strictes** avec le tir B du 2026-09-19
soir (même population non purgée, 247 messages par boîte, `UID_BASE=365`, corpus fileté
0,3, latence 96 ms, chauffe hydratée) — la ligne de référence est dans
`Api/Mail/tests/loadtest-k6/reports/POSTGRES-INDEX.md` :

| Grandeur de référence (19/09 soir, task-322) | Valeur | Attendu après |
|---|---|---|
| SQL ms / requête HTTP | 16,5 | < 4 |
| Temps SQL cumulé (3 h) | 55,7 min | ~11 min |
| Forme « documents » de la page d'en-têtes | 97 ms, 640 blocs / appel | < 3 ms, ~20 blocs |
| Taux de cache (blocs) | 95,72 % | ≥ 99 % |
| Lecture disque | 3,08 Mo/s | < 1 Mo/s |
| p50 / p95 page d'en-têtes (`read_list`/`emails`) | 69,9 / 110 ms | à lire, sans seuil |
| Appels à la route de contenu sur le parcours | à relever | plat (le scénario n'ouvre pas la frise) |

**Deux mesures à ajouter au harnais** parce qu'elles manquent : la taille de la réponse de
la page d'en-têtes (`data_received` k6 tagué par opération, ou l'histogramme de taille de
réponse OpenTelemetry par route) avant/après ; le nombre d'appels à la route de contenu.
Publication dans `Docs/audits/`, ligne ajoutée à `POSTGRES-INDEX.md`, mémoire « la page
d'en-têtes charge les blobs » mise à jour. **Aucun seuil de gain n'est un critère de
DOD** : le correctif se merge sur sa justesse, la mesure dit ce qu'il valait.

## Definition of Done

- [ ] Build passes (0 errors) sur les trois repos — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` ; `cd Client/Mobile && npm ci && npm run build` ; `cd Client/Blazor && dotnet build HealthPlatform.Client.sln`
- [ ] Tests pass (0 failures) sur les trois repos — `dotnet test HealthPlatform.Api.Mail.sln` ; `npm test -- --watch=false --browsers=ChromeHeadless` ; `dotnet test HealthPlatform.Client.sln`
- [ ] **Mobile** : la frise patient n'appelle plus la route de contenu au chargement d'une page ni à l'infinite scroll (`loadMailsContent` supprimé) — spec Jasmine : aucun appel de contenu après `loadFirstPage` / `loadMore`
- [ ] **Mobile** : déplier un document sans HTML appelle la route de contenu **une fois**, affiche le HTML (ou le corps brut), et un second dépliage ne rappelle pas — spec Jasmine
- [ ] **Mobile** : ouvrir la modale d'un document sans HTML charge le contenu et l'affiche ; un document avec HTML déjà présent ne déclenche aucun appel — spec Jasmine
- [ ] **Mobile** : l'échec de la route de contenu affiche « Aperçu indisponible — ouvrez le document » sans casser la frise — spec Jasmine
- [ ] **Mobile** : `data-testid` sur le bouton de dépliage, l'aperçu, le spinner et l'état d'échec ; aucune chaîne codée en dur nouvelle hors i18n existant
- [ ] **Blazor** : test bUnit prouvant que `LoadContent` recharge par la route de contenu quand les documents d'un `MailDto` n'ont ni `Body` ni `BodyHtml`, et que le HTML s'affiche ensuite ; vérification consignée dans le task file que `PatientTimeline.razor` ne lit ni `Body` ni `BodyHtml`
- [ ] **api-mail** : `LoadBulkContentLookupsAsync` en mode Header ne matérialise plus `Body` ni `HtmlBody` de `MailMedicalDocuments` ; le mode `WithContent` et la route de contenu sont inchangés
- [ ] **api-mail** : `MedicalDocumentTagListProjection` alignée ; la requête `MailContents` de liste vérifiée sans `BodyHtml` ni `Embedding` ; l'émetteur de la forme n°15 (colonnes `Body`, `BodyHtml`, `Embedding`, `Summary` de `MailContents`) identifié et consigné (liste corrigée, ou détail légitime)
- [ ] **api-mail** : forme n°4 (document chargé entier, une ligne, 67 770 appels) attribuée et projetée, **ou** consignée comme finding hors PR avec l'attribution partielle
- [ ] **Test d'intégration Postgres** (`HeaderListingProjectionTests`, SQL observé) : page d'en-têtes et « marquer lu » n'émettent aucun `SELECT` listant `"HtmlBody"` ou `"Body"` de `MailMedicalDocuments` ; `WithContent` et la route de contenu les listent toujours
- [ ] **Preuve du ROUGE** : ce test est écrit d'abord et **échoue** sur le code actuel (log du run rouge dans le task file — mémoire `feedback-test-qui-stube-sa-propre-premisse`)
- [ ] **Non-régression fonctionnelle** : `MedicalDocuments[]` de la page d'en-têtes identique avant/après sur tous ses membres **sauf** `Body` et `BodyHtml` (nuls) — test de caractérisation mis à jour
- [ ] Contrat inchangé : aucun fichier de `Dtos/` modifié ; `client-angular` non touché
- [ ] Aucune donnée de santé en clair dans les logs : le SQL capturé par le test n'est jamais journalisé avec ses paramètres ; le HTML des documents n'apparaît dans aucun log mobile
- [ ] Le body des trois PRs porte l'encadré « ordre de merge : client-mobile avant api-mail »
- [ ] Tir `terrain` 1 000 avant/après publié dans `Docs/audits/`, ligne ajoutée à `POSTGRES-INDEX.md`, taille de réponse de la page d'en-têtes et appels de contenu relevés, mémoire mise à jour (peut être fait par l'humain au HAG si le banc n'est pas disponible dans le cycle ; à défaut, noter « mesure en attente » dans le task file, jamais de silence)

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil par défaut), ou le profil `https-load-test` du skill de banc pour disposer d'un tenant hydraté.
- Lancer le mobile : `cd Client/Mobile && npm start` ; Blazor : `cd Client/Blazor && dotnet run`.
- **Frise patient mobile** : ouvrir la fiche d'un patient ayant plusieurs documents CDA. La frise s'affiche avec titres, dates, catégories ; dans l'onglet réseau du navigateur, **aucun appel** à `…/emails/content/…` au chargement ni au scroll. Déplier un document : un appel de contenu, le HTML s'affiche. Replier puis redéplier : aucun nouvel appel. Ouvrir la modale du même document : aucun nouvel appel, le HTML s'affiche. Ouvrir la modale d'un autre document sans l'avoir déplié : un appel, le HTML s'affiche. Un document avec PDF externe : le PDF s'affiche comme avant.
- **Frise patient mobile, panne** : couper le backend après affichage de la frise, déplier un document : « Aperçu indisponible — ouvrez le document », la frise reste utilisable.
- **Boîte de réception Blazor** : ouvrir un message porteur d'un document CDA : le HTML du document s'affiche (rechargé par la route de contenu). Frise patient Blazor : identique à avant.
- **Boîte de réception mobile et Angular** : ouvrir un message avec document : HTML affiché, identique à avant.
- **Marquer lu** depuis la liste (les trois clients) : l'état change, la ligne reste identique.
- **Preuve côté base** : avec le log EF `Microsoft.EntityFrameworkCore.Database.Command` en Debug ou Seq (`seq-local`), ouvrir la boîte et la frise : les `SELECT … FROM "MailMedicalDocuments"` émis pendant le chargement des listes **ne listent ni `"HtmlBody"` ni `"Body"`**. Les mêmes requêtes émises à l'ouverture d'un message ou par la route de contenu les listent.
- **Taille de réponse** : dans l'onglet réseau, la réponse de `GET …/emails/{ids}` pour une page de 25 messages avec documents pèse quelques dizaines de Ko, pas plusieurs Mo.
- **Mesure** (si le banc est disponible) : `tests/loadtest-k6/run.sh terrain` en iso-conditions, puis comparer la nouvelle ligne de `POSTGRES-INDEX.md` à celle du 2026-09-19 soir.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — optimisation interne, aucune exigence fonctionnelle nouvelle
- **Exigences DSR honorées** : non applicable — le contenu affiché au PS est identique après ouverture ; seul le moment du chargement change
- **INS** : non applicable — la US ne manipule aucun trait d'identité ; les traits patient déjà présents dans le DTO d'en-tête restent projetés à l'identique
- **Authentification PS** : inchangée (PSC / e-CPS existant) — la route de contenu et les endpoints de liste gardent leurs garde-fous
- **Habilitations** : inchangées — même filtrage par tenant (`GetDataContextAsync`) ; la frise mobile appelle la route de contenu avec le même contexte de session que la liste
- **Interop CI-SIS** : non applicable — les documents CDA ne sont ni lus ni produits ici ; leur rendu HTML cesse seulement d'être lu par un chemin qui ne l'affichait pas
- **Tracé PGSSI-S** : inchangé — `MailRead` (task-300/301) reste tracé sur son chemin ; à vérifier pendant `/develop` : si la route de contenu émet une trace d'accès au contenu, le dépliage d'un document dans la frise en émettra une par document ouvert, ce qui est **plus juste** qu'aujourd'hui (le contenu était livré sans consultation). Consigner le constat dans le task file
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé ; effet positif : les compte-rendus (DSCP) ne quittent plus la base ni le serveur pour un usage qui ne les affichait pas, et ne transitent plus vers un terminal mobile qui ne les montrait pas
- **AIPD / impact RGPD** : inchangé — minimisation de la circulation de données de santé, aucun traitement nouveau

## Branches

- `api-mail` (pushed) : `feat/task-323-doc-html-on-open` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-323-doc-html-on-open
- `client-blazor` (pushed) : `feat/task-323-doc-html-on-open` — https://github.com/codengine-technologies/HealthPlatform.Client/tree/feat/task-323-doc-html-on-open
- `client-mobile` (pushed) : `feat/task-323-doc-html-on-open` — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-323-doc-html-on-open

`dtos-mss` non listé et non auto-inclus (contrat inchangé — cf. DOD). `client-angular` non listé (déjà correct).

## Timings

*(généré par `tools/timing/report.sh --task task-323 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 22 s | — | — | — | — |
| /develop | ok | 28 min 18 s | 9 (1 min 25 s) | 11 (5 min 09 s) | — | api-mail 4B/5T, client-mobile 2B/4T, client-blazor 3B/2T |
| /sonar | ok | 7 min 26 s | — | — | 1 (4 min 45 s) | — |
| /lint-angular | skipped | 16 s | — | — | — | client-angular hors Repos de la task ; working tree porte uniquement du WIP humain anterieur |
| /lint-mobile | ok | 30 s | — | — | — | — |
| /verify-visual | skipped | 36 s | — | — | — | Tools/visual-verify absent du checkout (capture.mjs introuvable) - best-effort, aucune capture produite |
| /review | ok | 6 min 16 s | 4 (24 s) | 4 (2 min 17 s) | — | api-mail 2B/2T, client-blazor 1B/1T, client-mobile 1B/1T |
| /tech-writer | ok | 4 min 32 s | — | — | — | — |
| **Total cycle** | | **48 min 18 s** | **13 (1 min 49 s)** | **15 (7 min 27 s)** | **1 (4 min 45 s)** | |

Autres commandes mesurées : lint ×1 (17 s)

## Develop log

- **Repos touchés** : `api-mail`, `client-mobile`, `client-blazor`
- **DTOs publiés** : aucun changement de contrat — `Dtos/` non modifié, aucune branche sur `dtos-mss` (conforme à la règle « branche paresseuse »)
- **Interop / SDK** : aucun changement

### Preuve du ROUGE (exigée par la DOD)

`HeaderListingProjectionTests` écrit **avant** le correctif, sur le code de
`origin/develop`. Run du 2026-09-20 :

```
Failed  HeaderPageDoesNotReadAttachmentBytesNorDocumentEmbeddings
        Assert.DoesNotContain() Failure: Sub-string found
        String: ···"rContactId", m."Body", m."HtmlBody", m."CreatedAt""···
        Found:  ""HtmlBody""

Failed  HeaderSingleMailDoesNotReadDocumentBodies
        Assert.DoesNotContain() Failure: Sub-string found
        String: ···"m."DuplicateRejected", m."Embedding", m."Format", "···
        Found:  ""Embedding""      ← l'entité ENTIÈRE était matérialisée

Failed  HeaderPageStillRendersAttachmentsAndDocumentsIdentically
        Assert.Null() Failure: Value is not null
        Expected: null   Actual: "<p>Résultats</p>"

Failed!  - Failed: 3, Passed: 3, Total: 6
```

Après correctif : `Passed! - Failed: 0, Passed: 6, Total: 6`.

Le test bUnit Blazor a été vérifié rouge **par mutation** (retrait de la
condition sur les documents vides dans `LoadContent`) : `Failed: 1, Passed: 1`.
Le fichier de production a été restauré (`git diff` vide) — mémoire
`feedback-test-qui-stube-sa-propre-premisse`.

### Findings d'attribution — points 3 et 4 du périmètre

| Forme | Attribution établie | Traitement |
|---|---|---|
| Page d'en-têtes (82 % du SQL) | `LoadBulkContentLookupsAsync`, branche `headerOnly` | `Body`/`HtmlBody` retirés de la projection |
| **n°4** — un document chargé entier, une ligne, 39 blocs, 67 770 appels | **`PopulateMailContentAsync`**, appelé par `GetMailAsync(Header)` dès que le message porte des documents (contexte d'audit d'une pièce jointe, copie, suppression). Les candidats cités par le task file (`FirstOrDefaultAsync` ~l. 2815/2846, `BiologyAckRepository`) sont **hors de cause**. | Projeté en mode Header, **dans la même PR** — l'attribution a tenu en moins d'une heure |
| **n°15** — `MailContents` avec `Body`, `BodyHtml`, `Summary`, `Embedding` | Même chemin : la lecture de `MailContents` de `PopulateMailContentAsync`, qui ne distinguait pas les deux modes | Projeté en mode Header (chaînes vides), aligné sur le chemin groupé |
| `MedicalDocumentTagListProjection` | Déjà sans corps ni embedding — vérifié, aucun changement | — |
| `MailContents` en mode Header du chemin groupé | Déjà projeté sans `BodyHtml` (task-261) — vérifié | — |

**Correction d'un fait du task file.** Le task file attribue ~12,4 k appels à
« `GetMailAsync(Header)` derrière *marquer lu* ». Ce n'est plus vrai depuis
**task-230** : `UpdateEmailReadStatusAsync` ne lit plus le message, il prend un
cliché d'audit de quatre champs (`GetMailAuditSnapshotAsync`). Le geste
n'émettait donc déjà **aucune** requête sur `MailMedicalDocuments`. Le test
`MarkAsReadAuditSnapshotNeverReadsMedicalDocuments` fige cet état — il est vert
d'emblée, et c'est ce qu'il doit être : sa valeur est de détecter le jour où ce
chemin re-hydraterait un message. Les 12,4 k appels de `GetMailAsync(Header)`
viennent des autres appelants du tableau ci-dessus.

**Tracé PGSSI-S** (point à vérifier demandé par la section Conformité) : la route
de contenu (`GET …/emails/content/{uid}`) **n'émet aucune trace d'accès** propre —
`MailRead` reste tracé par `UpdateEmailReadStatusAsync`, sur le geste « marquer
lu », inchangé par cette US. Le dépliage d'un document dans la frise n'ajoute
donc aucune trace. Le constat espéré par le task file (« ce serait plus juste »)
ne se réalise pas de lui-même : il demanderait d'instrumenter la route de
contenu, ce qui est une US à part.

### Vérification Blazor consignée (point 2 du périmètre)

- `MailListComponent.LoadContent` (~l. 866) recharge bien par la route de contenu
  quand tous les documents ont `Body` et `BodyHtml` vides — figé par
  `MailListContentReloadTests`.
- `MailBodyComponent` : lit `BodyHtml` du **message**, pas des documents.
- `PatientTimeline.razor` : **ne lit ni `Body` ni `BodyHtml`** — vérifié par grep,
  il ne lit que `Category`, `DocumentDate` et `MedicalDocuments` (l. 230-351).
  Aucun code de production Blazor n'a été modifié.

### Build / tests locaux

| Repo | Build | Tests |
|---|---|---|
| `api-mail` | ✓ 0 erreur | ✓ 2 497 + 514 passés, 0 échec |
| `client-mobile` | ✓ | ✓ **880 / 880** (863 avant, +17 specs) |
| `client-blazor` | ✓ 0 erreur | ✓ 264 passés, 2 skipped (pré-existants) |

### Mesure avant/après — **en attente**

Le tir `terrain` 1 000 en iso-conditions n'a **pas** été rejoué dans ce cycle : le
banc exige un tireur distant et une chauffe hydratée de plusieurs heures, hors de
la fenêtre du cycle autonome. Conformément à la DOD, le fait est noté ici plutôt
que taire : **mesure en attente**, à produire au HAG ou dans un cycle de mesure
dédié, avec la ligne de référence du 2026-09-19 soir
(`Api/Mail/tests/loadtest-k6/reports/POSTGRES-INDEX.md`). Les deux mesures à
ajouter au harnais (taille de réponse de la page d'en-têtes, nombre d'appels à la
route de contenu) restent à câbler.

### Passe qualité (`/simplify`) — intégrée à `/develop`

Quatre revues en parallèle (reuse / simplification / efficacité / altitude). Les
trois premières ont convergé sur les mêmes points ; la revue d'altitude a nommé
**la cause commune** des défauts du client mobile : `hydrate` mutait le document
et ne rendait qu'un booléen, donc chaque consommateur en `OnPush` devait
inventer son propre moyen de s'apercevoir que quelque chose avait changé.

**Appliqué et committé**

| Repo | Commit | Ce qui change |
|---|---|---|
| `api-mail` | `b7dc147` | `ContentHeaderProjection` extraite (recopie mot pour mot entre les deux chemins d'en-tête) ; clause `Where` construite une fois par requête ; bloc de documentation orphelin remis sur sa méthode |
| `client-mobile` | `1d3c4d2` | `hydrate` rend le document complété (signal réel au lieu d'un compteur de version) ; cache borné à 3 messages ; pas de chargement du contenu structuré sur un document à PDF externe ; une seule machine à états pour l'aperçu ; une seule politique de reprise ; `documentLocators` dérivé de `mailIndex` et **clé composite** |
| `client-blazor` | — | aucun cleanup (diff de test seul) |

**Deux trouvailles qui valaient plus qu'un nettoyage**

1. **Le cache du service rendait au terminal ce qu'on retirait du réseau.** Non
   borné dans un singleton d'application, il retenait des `MailContentDto`
   entiers — soit exactement les ~222 Ko de HTML par document que cette US
   cesse d'envoyer — pour toute la session. Borné à 3 messages.
2. **La clé de `documentLocators` était nue (`documentId`).** Or un même
   `documentId` existe sous plusieurs messages (versions, doublons — `SetId`,
   `Version`, `DuplicateOfId` sont de première classe ici). Le dernier message
   gagnait, et l'aperçu déplié pouvait charger le contenu **du mauvais
   message**. Clé composite `mailId::documentId`, dérivée de `mailIndex` qui
   l'utilisait déjà. Spec ajoutée.

**Écarté, et pourquoi**

- **Supprimer la mutation du document par le service** (revue d'altitude, moitié
  restante) : c'est elle qui rend gratuit le second geste sur le même document
  quelle que soit l'ancienneté du cache — retirer les deux (mutation *et*
  cache non borné) aurait fait retomber un appel réseau sur un geste que la DOD
  décrit comme gratuit. La moitié utile — rendre le document — est prise.
- **Faire porter les coordonnées par l'élément de la frise** plutôt que par un
  second `@Input` : restructuration du contrat de données du composant, hors du
  remit d'une passe qualité ; le risque qu'elle visait (mauvais message) est
  traité par la clé composite, à bien moindre coût.
- **Double parcours de `mails()`** (revue d'efficacité, signalé non urgent) :
  résolu de fait par la dérivation depuis `mailIndex`.

**Re-validation après cleanups** : `api-mail` build ✓ / 4 524 tests ✓ ;
`client-mobile` build ✓ / **885 specs ✓** ; `client-blazor` non touché, son vert
précédent tient.

**Push** : un par repo, portant la feature et la passe qualité.

- `api-mail` : `b7dc1471`
- `client-mobile` : `1d3c4d2`
- `client-blazor` : `245f25f`

**Étape suivante** : `/sonar task-323` (api-mail touché).

## Sonar log

**Mode A** (chaîné depuis `/develop`), scan sur `feat/task-323-doc-html-on-open`.
Serveur SonarQube **9.9.8** — démarré par l'étape (couple `sonarqube_db` puis
`sonarqube`), et c'est la version qui **ignore silencieusement `sonar.token`** :
`sonar.login` employé, conformément au piège documenté.

### KPIs qualité — baseline → final

| Métrique | Baseline (avant scan) | Final | Cible |
|---|---|---|---|
| Bugs | 0 | **0** | 0 |
| Vulnerabilities | 0 | **0** | 0 |
| Security Hotspots | 3 | **3** (0 en new code) | revus |
| Code Smells | 216 | **216** | ↓ |
| Coverage | 87,8 % | **87,8 %** | ≥ 95 % |
| Duplication | 0,4 % | **0,4 %** | < 3 % |
| Reliability rating | A | **A** | A |
| Security rating | A | **A** | A |
| Maintainability rating | A | **A** | A |

### Quality Gate : **OK** ✅

| Condition | Valeur | Seuil | État |
|---|---|---|---|
| `new_reliability_rating` | 1 (A) | ≤ A | OK |
| `new_security_rating` | 1 (A) | ≤ A | OK |
| `new_maintainability_rating` | 1 (A) | ≤ A | OK |
| `new_coverage` | **85,1 %** | ≥ 80 % | OK |
| `new_duplicated_lines_density` | 0,23 % | < 3 % | OK |

### Itérations de nettoyage : **0** — et c'est le bon résultat

`new_bugs = 0`, `new_vulnerabilities = 0`, `new_security_hotspots = 0`.
Restent **23 `new_code_smells`** dans la fenêtre new-code — dont **aucun dans
les deux fichiers de cette task** (`MailRepository.cs`,
`HeaderListingProjectionTests.cs`). La fenêtre porte `new_lines = 38 982` :
elle ne cadre pas le diff de la task, elle couvre tout le lot E016. Les 23
findings se répartissent en :

- **13 × `CA1068`** (`CancellationToken` en dernier paramètre) sur les
  **interfaces** `ITenantRegistryClient` / `IMailboxSelectionService` — contrat
  publié de l'EPIC E016 ; les corriger est un changement de contrat, pas un
  nettoyage ;
- **1 × `S3776`** (`PostgresTenantRegistryClient`, complexité 17 > 15) —
  **blacklistée** (`agents/sonar-blacklist.yml`), traitée par `/sonar-s3776`,
  une méthode = une PR ;
- **2 × `S3925`** (`ISerializable`) dans `TenantRegistryExceptions` ;
- **7 × `INFO`** dans des fichiers de tests (`AV0011`, `CA1822`).

**Pourquoi ne rien toucher.** Ces fichiers n'appartiennent pas à cette US. Les
corriger ici violerait la règle 6 (périmètres isolés) et gonflerait une PR de
2 fichiers à une quinzaine, sur du code qu'aucun relecteur de cette US n'attend.
Le nettoyage est best-effort par construction : il accepte les findings
restants. **Le code écrit par cette task n'introduit aucun finding** — c'est
exactement ce que l'étape doit établir.

**Conventions apprises** : aucune entrée à ajouter à `conventions/csharp.md` —
aucune règle n'a été corrigée manuellement sur du code frais.

**Étape suivante** : `/lint-angular task-323`.

## Lint log (client-angular)

**Skip propre.** `client-angular` n'est pas dans le `**Repos**:` de cette task
et le task file le justifie explicitement : la frise et le détail Angular
**rechargent déjà** le contenu à l'ouverture, donc le retrait du HTML des listes
ne les affecte pas. Aucun code Angular n'a été écrit par `/develop`.

Le working tree de `Client/Angular/` porte deux modifications **antérieures et
étrangères** à cette task — `apps/mss/.../environment.ts` et
`apps/weda2/.../environment.ts`, deux URL d'API basculées sur `localhost` pour
le développement local. Travail en cours de l'humain : laissé intact, ni lu ni
corrigé (mode code-only, aucune opération git sur ce repo).

- Itérations : **0**
- Erreurs ESLint restantes : non mesuré (hors périmètre)
- `conventions/angular.md` : aucune entrée à ajouter

**Étape suivante** : `/lint-mobile task-323`.

## Lint mobile log

Baseline sur `feat/task-323-doc-html-on-open` : **`All files pass linting.`**

- Erreurs ESLint : **0** (baseline = final)
- Warnings : 0
- Itérations consommées : **0** sur 5
- Commit / push : **aucun** — rien à corriger, la branche poussée par
  `/develop` est déjà propre

Les conventions de `conventions/angular.md` ont été appliquées d'emblée par
`/develop`, comme le protocole l'exige : control flow natif (`@if` / `@for` /
`@switch` — le nouveau bloc d'aperçu et l'état de chargement de la modale sont
écrits ainsi), sélecteurs préfixés `mss-`, libellés FR en dur sans i18n,
`data-testid` sur chaque élément interactif et chaque état notable
(`doc-group-expand`, `doc-group-preview-loading`, `doc-group-preview-html`,
`doc-group-preview-raw`, `doc-group-preview-failed`,
`document-modal-content-loading`).

**Conventions apprises** : aucune entrée à ajouter à `conventions/angular.md` —
aucune règle corrigée manuellement (ni même par l'auto-fixer).

**Étape suivante** : `/verify-visual task-323`.

## Visual verify log

**Non exécuté — absence d'outillage, best-effort.** L'étape n'a produit
**aucune capture** : `Tools/visual-verify/` (avec `capture.mjs`, `screens.json`,
les fixtures et la config Playwright de la forge) **n'existe pas** dans ce
checkout du plan de contrôle. `find . -name capture.mjs` ne rend rien.

Ce n'est donc **pas** un verdict « écrans conformes » : c'est une panne
d'outillage, que le playbook classe explicitement en best-effort (« écran/API
non mappé, panne outillage → logué, la chaîne continue »). Le seul cas bloquant
— écran blanc / crash de navigation — n'a pas pu être écarté par la capture.

**Ce qui est mesuré par ailleurs, et qui n'est pas rien** : les 885 specs
Jasmine de `client-mobile` passent, dont 17 nouvelles couvrant précisément les
états d'affichage introduits ici — aperçu chargé (HTML et texte brut), état de
chargement, état d'échec, document déjà porteur de son contenu, document à PDF
externe. Le rendu de la frise n'est donc pas non vérifié ; il est vérifié au
niveau composant, pas à l'écran.

**Ce qui reste à l'œil de l'humain au HAG** (déjà présent dans le
`## Manual Test Plan`, section « Frise patient mobile ») :

- la frise s'affiche sans appel `…/emails/content/…` au chargement ni au scroll ;
- déplier un document : spinner, puis HTML ; replier/redéplier : aucun appel ;
- ouvrir la modale du même document : aucun appel, HTML affiché ;
- backend coupé, déplier : « Aperçu indisponible — ouvrez le document », frise
  utilisable ;
- document à PDF externe : le PDF s'affiche comme avant, et l'onglet « Détail »
  charge le contenu structuré à la demande (comportement nouveau, issu de la
  passe qualité).

Écrans concernés dans la galerie existante :
`Docs/epics/img/screens/client-mobile/patient-timeline.png` — **non rafraîchi**
par ce cycle.

**Étape suivante** : `/review task-323`.

## PRs

| Repo | PR | Label | Ordre de merge |
|---|---|---|---|
| `client-mobile` | https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/77 | `awaiting-human-merge` | **1er** |
| `api-mail` | https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/247 | `awaiting-human-merge` | **2e — après le mobile** |
| `client-blazor` | https://github.com/codengine-technologies/HealthPlatform.Client/pull/81 | `awaiting-human-merge` | indépendant (test seul) |

`client-angular` : non listé — la frise et le détail Angular rechargent déjà le
contenu à l'ouverture. `dtos-mss` : aucun contrat modifié, aucune branche créée.

## Code Review Summary

**Verdict : APPROVED** — 4 fichiers de production et 8 fichiers de test relus,
0 blocage, 3 suggestions non bloquantes consignées dans les PRs.

**Un vrai défaut trouvé en revue et corrigé** : une marque d'ordre d'octets (BOM)
avait été introduite par erreur en tête des deux fichiers `api-mail`, qui n'en
portaient pas sur `develop` — premier `+`/`-` du diff, du bruit étranger à l'US.
Retirée (`9a5fd2fe`), build et tests re-validés.

**Vérifications de non-régression menées à la main sur le changement le plus
risqué** (`GetMailAsync(Header)` rend désormais un corps de message vide) : ses
trois appelants — contexte d'audit d'une pièce jointe (`TryGetMailContextAsync`),
copie de message (`ImapFolderService`), suppression (`ImapService`) — ne lisent
aucun corps. Le tracé d'audit ne lit que `MessageId`, `Subject`, `From`, `To`,
tous toujours peuplés.

### Signalement honnête — un test mobile intermittent

La première exécution de validation de `/review` a rendu **1 échec sur 885**.
Quatre exécutions consécutives ensuite : **885/885 vertes**. **Je ne peux pas
nommer la spec en cause** — la sortie de cette première exécution était filtrée
et le détail est perdu. Ce n'est donc ni « un flaky pré-existant identifié »,
ni « un échec de cette task » : c'est un échec intermittent non attribué, et il
est consigné comme tel plutôt qu'écarté. À surveiller au prochain cycle sur ce
repo.

## Validation

| Repo | Build | Tests |
|---|---|---|
| `api-mail` | ✓ 0 erreur | ✓ 4 524 passés (183 + 492 + 2 497 + 838 + 514), 0 échec, 16 skipped |
| `client-mobile` | ✓ | ✓ 885 / 885 (voir signalement ci-dessus) |
| `client-blazor` | ✓ 0 erreur | ✓ 264 passés, 2 skipped |

Les trois branches contenaient déjà la pointe de `develop` — aucune fusion
nécessaire, aucun conflit.

## DOD — état

Tous les items commandables sont ✅ **sauf** le dernier, explicitement traité par
la clause d'échappement de la DOD elle-même :

- Tir `terrain` 1 000 avant/après : **mesure en attente** — le banc exige le
  tireur distant et une chauffe hydratée de plusieurs heures, hors de la fenêtre
  du cycle. La DOD prévoit ce cas (« peut être fait par l'humain au HAG […] à
  défaut, noter “mesure en attente” dans le task file, jamais de silence »).
  Les deux mesures à ajouter au harnais (taille de réponse de la page d'en-têtes,
  nombre d'appels à la route de contenu) restent à câbler.

Item de vérification visuelle : **non couvert** — outillage absent (voir
`## Visual verify log`). Il n'est pas dans la DOD, mais l'absence est signalée
dans la PR mobile plutôt que passée sous silence.
