# todo-task-290.md — Les mails reçus pendant une panne de feature flags restent définitivement hors de la recherche sémantique, sans aucune trace de ce qui a été sauté

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015
**Single frontend**: true
**Priorité**: **1** — c'est une **perte de donnée médicale silencieuse** sur le
chemin de recherche, du même ordre que `task-196`. Le praticien ne voit pas une
erreur : il voit une recherche qui ne remonte pas un document reçu, ce qui est
indiscernable d'un document qui n'a jamais existé.

> **Origine** : conséquence différée de l'incident Staging du **2026-09-02**
> (voir `todo-task-289.md`, qui traite la cause). Pendant que l'étage IA était
> éteint par un flag sans rapport, des mails cliniques ont été consommés du bus
> et **acquittés** sans être enrichis. `task-289` empêche la récidive ;
> **elle ne répare rien de ce qui a déjà été perdu**, et n'aiderait pas non plus
> lors d'une extinction *volontaire* du flag (bascule d'exploitation, maîtrise
> du coût OpenAI), qui produit exactement le même trou.

## Objective

Qu'un mail dont l'étage IA a été sauté soit **repérable** et **rattrapable**,
au lieu d'être indiscernable d'un mail correctement enrichi.

Aujourd'hui, quand `ai_pipeline` est désactivé, le consommateur journalise en
`Debug` puis fait `return` : le message est acquitté, et **rien n'est
persisté** pour dire que ce mail est passé à côté de l'enrichissement. Le mail
existe en base, il s'affiche normalement dans la boîte du praticien, il est
compté comme « enrichi » par la couverture de synchronisation — mais il n'a ni
vecteur d'embedding, ni tags, et ses contacts (praticien et patient) n'ont
jamais été extraits. Réactiver le flag ne le rejoue pas : le message n'existe
plus sur le bus.

**US backend-only (justification)** : détection et rejeu côté serveur. Aucun
écran n'est modifié ; le bénéfice côté frontends est le **retour** de documents
manquants dans la recherche, sans changement d'interface.

### Périmètre exact de la perte — établi par lecture du code

Trois choses sont perdues, une quatrième ne l'est pas. La distinction est
importante : elle borne le travail.

| Étage | Où il tourne | Perdu ? |
|---|---|---|
| **Embedding** (index sémantique) | `AddNewMailConsumer.RunEmbeddingTask` — une fois, à la consommation du message | **Oui, définitivement** |
| **Extraction de contacts** praticien + patient | même tâche (`ProcessEmbeddingAsync` publie vers `IPractitionerContactPublisher` / `IPatientContactPublisher`) | **Oui, définitivement** |
| **Auto-tagging** | `AddNewMailConsumer.RunTaggingTask` — même déclencheur | **Oui, définitivement** |
| **Résumé IA** | `EmailSummaryService.ProcessEmailSummariesAsync` — **à la demande**, depuis le contenu IMAP, avec cache Redis | **Non** — se régénère au premier accès dès que le flag est rallumé |

Le résumé est donc **hors périmètre de rattrapage** : les 404 « AI summary is
not available » observés le 2026-09-02 se réparent d'eux-mêmes. C'est
l'embedding, les contacts et les tags qui demandent un rejeu — et l'extraction
de contacts est la perte la plus lourde, parce qu'elle alimente le rattachement
patient, pas seulement une commodité de recherche.

### Le défaut structurel, au-delà de l'incident

Le mail sauté **n'est pas marqué**. C'est ce qui rend le rattrapage impossible
sans cette US : il n'existe aucun critère pour distinguer

- un mail dont l'étage IA a été sauté (flag éteint),
- un mail dont l'étage IA a échoué (erreur OpenAI — cf. `task-196`),
- un mail dont l'embedding est légitimement vide (aucun contenu exploitable).

Un rattrapage fondé sur « les mails sans vecteur » confondrait les trois et
relancerait indéfiniment des mails qui n'ont rien à indexer, au coût OpenAI
correspondant.

**La marque doit donc précéder le rejeu** — c'est l'ordre naturel de
l'implémentation, et le point que `/develop` ne doit pas inverser.

### Contenu attendu

1. **Marquer le saut, à la source.** Quand le consommateur renonce à l'étage IA
   parce que le flag est éteint, l'état du mail doit le consigner de façon
   **durable et interrogeable** (et non un simple log `Debug`), avec le motif
   (`flag désactivé`) et l'horodatage. Le choix de la représentation revient à
   `/develop` ; l'exigence produit est qu'on puisse répondre à « quels mails de
   ce praticien ont sauté l'étage IA, et pourquoi ».
2. **Compter le saut.** `MailProcessingMetrics` enregistre déjà `Skipped` pour
   l'embedding et le tagging quand leurs sous-flags sont éteints, mais **le
   renoncement global sur `ai_pipeline` ne compte rien** — c'est un angle mort.
   L'exploitation doit voir monter un compteur, pas devoir lire des logs
   `Debug`.
3. **Rejouer, sur demande explicite.** Un moyen déclenché par l'exploitation
   (pas un automatisme au démarrage) pour relancer l'étage IA sur les mails
   marqués, borné par praticien et par fenêtre temporelle. Le coût OpenAI d'un
   rejeu de masse doit être un geste conscient — ne jamais rattraper « tout »
   implicitement.
4. **Idempotence.** Un mail déjà rattrapé ne doit pas être re-embeddé ni
   re-taggé s'il est soumis deux fois : sinon un rejeu interrompu puis relancé
   double la facture et duplique les tags.
5. **Le rejeu respecte les flags.** Si `ai_pipeline` est encore éteint, le rejeu
   ne contourne pas le flag : il refuse franchement, avec un message qui dit
   pourquoi. Un mécanisme de rattrapage qui outrepasse l'interrupteur qu'on
   vient de poser est un piège.
6. **La couverture de synchronisation doit cesser de mentir.** `GET
   /api/v1/sync/coverage` annonçait `enriched=99%` le 2026-09-02 alors que
   l'étage IA n'avait rien fait. Le décompte doit distinguer « téléchargé »,
   « enrichi IMAP » et « enrichi IA » — sans quoi l'indicateur censé nous
   alerter est précisément celui qui nous a rassurés.

### Hors périmètre (explicite)

- **La cause de l'incident** (un flag absent qui éteint les autres) est traitée
  par `todo-task-289.md`. Les deux US sont indépendantes et peuvent avancer en
  parallèle : `task-289` ferme la porte, `task-290` répare la pièce.
- **Le rattrapage des résumés IA** — inutile, ils se régénèrent à la demande
  (voir le tableau ci-dessus).
- **La troncature en tokens et la trace des documents non indexés** sont le
  sujet de `task-196`, déjà traité. Cette US ne le rejoue pas : elle traite le
  cas « l'étage n'a pas tourné du tout », pas « il a tourné et tronqué ».

## Definition of Done

- [ ] Build passes on api-mail (0 errors)
- [ ] Tests pass (0 failures)
- [ ] Test : `ai_pipeline` désactivé → le mail consommé est marqué comme ayant
      sauté l'étage IA, avec son motif, et le marquage est interrogeable
- [ ] Test : le compteur de saut global sur `ai_pipeline` est incrémenté
      (l'angle mort actuel)
- [ ] Test : un mail correctement enrichi n'est **pas** marqué
- [ ] Test : le rejeu relance embedding + contacts + tags sur un mail marqué, et
      lève le marquage au succès
- [ ] Test : le rejeu d'un mail **déjà** enrichi est un no-op — aucun appel au
      fournisseur d'embedding, aucun tag dupliqué (idempotence)
- [ ] Test : rejeu demandé alors que `ai_pipeline` est éteint → refus explicite,
      aucun appel OpenAI
- [ ] Test : le rejeu est borné par praticien et par fenêtre temporelle ; une
      demande non bornée est refusée
- [ ] Test : `GET /api/v1/sync/coverage` distingue « enrichi IMAP » et
      « enrichi IA », et le second chute bien quand des mails sont marqués
- [ ] Le déclencheur de rejeu a au moins 1 test d'intégration
      (happy path + 1 mode d'échec) — rule 1b
- [ ] Erreurs en `ProblemDetails` RFC 7807 via le `GlobalExceptionHandler`
      (rule 12) — notamment le refus « flag éteint » et le refus « demande non
      bornée »
- [ ] Aucune donnée de santé en clair dans les logs du rejeu : ni contenu de
      mail, ni contenu CDA, ni INS. Les identifiants de mail et l'adresse
      MSSanté suivent le masquage déjà en place
- [ ] Aucun appel OpenAI dans les tests (fournisseur d'embedding et de tagging
      mockés)

## Manual Test Plan

- **Lancer le backend** : `cd Api/Mail && dotnet run --project src/AppHost`.
- **Fabriquer le trou** :
  1. dans l'UI Flagsmith (`http://localhost:8000`, projet `HealthPlatform.Mss`,
     environnement `Development`), poser `ai_pipeline` à **`false`** ;
  2. injecter des mails synthétiques porteurs de pièces jointes IHE_XDM via le
     `loadtest-skill` (seed du banc) — attendre les lignes
     `[Consumer] 📨 Processing MailId=…` ;
  3. remettre `ai_pipeline` à **`true`**.
- **Constater le trou** (avant rattrapage) :
  - `GET /api/v1/sync/coverage` → le décompte « enrichi IA » doit être
    **inférieur** au décompte « enrichi IMAP » (avant cette US, les deux étaient
    confondus à 99 %) ;
  - rechercher un terme présent **uniquement** dans le contenu d'un des mails
    injectés → **aucun résultat**, alors que le mail est bien visible dans la
    boîte. C'est le symptôme tel que le praticien le vit.
- **Rattraper** : déclencher le rejeu pour ce praticien sur la fenêtre
  correspondante.
- **Ce que l'humain doit voir** :
  - la même recherche remonte maintenant le document ;
  - les tags du mail apparaissent ;
  - les contacts extraits (praticien émetteur, patient concerné) sont
    disponibles pour le rattachement ;
  - `GET /api/v1/sync/coverage` : « enrichi IA » rejoint « enrichi IMAP ».
- **Contrôler les garde-fous** :
  - relancer le **même** rejeu → aucun nouvel appel au fournisseur d'embedding
    (vérifiable aux métriques), aucun tag en double ;
  - repasser `ai_pipeline` à `false` et redemander un rejeu → refus explicite en
    `application/problem+json`, aucun appel OpenAI.
- **Données de test** : mails synthétiques du banc uniquement. **Aucun mail
  MSSanté réel, aucune donnée patient réelle** — un rejeu déclenche des appels
  OpenAI sur le contenu des mails.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors exigence DSR directe. La US restaure néanmoins la
  complétude de l'indexation des documents cliniques reçus par MSSanté, qui
  sert le parcours documentaire du couloir
- **Exigences DSR honorées** : non applicable — aucune exigence DSR ne porte sur
  le rejeu d'un étage d'enrichissement interne
- **INS** : **applicable indirectement** — l'extraction de contacts patient
  alimente le rattachement, dont l'INS est le pivot. Le rejeu **ne crée jamais
  de patient** (garde-fou métier non négociable) et n'attribue aucune INS : il
  ne fait que restituer les contacts extraits, pour rattachement à un patient
  **existant**
- **Authentification PS** : le déclencheur de rejeu est un geste
  d'**exploitation**, pas un acte de soin. Il ne doit pas être exposé au
  praticien, et il ne doit pas se cacher derrière l'authentification PSC d'un
  praticien pour agir sur la base d'un autre — **point à confirmer avec
  l'humain si `/develop` envisage un endpoint accessible en session PS**
- **Habilitations** : le rejeu est borné à un praticien nommé ; il ne doit pas
  pouvoir traverser plusieurs bases praticien en une seule demande
- **Interop CI-SIS** : non applicable directement — le contenu rejoué a déjà
  transité par `interop-cda` et été validé Schematron lors de la réception. Le
  rejeu porte sur l'étage IA **en aval**, pas sur le parsing CDA
- **Tracé PGSSI-S** : évènements à journaliser — (a) saut de l'étage IA avec son
  motif, (b) demande de rejeu (qui, quand, quel périmètre), (c) résultat par
  mail. Le rejeu est une **modification de l'état d'un dossier documentaire** :
  sa trace relève de la journalisation métier, conservation 6 ans, et non de la
  simple trace technique
- **Consentement patient** : non applicable — aucun partage ni alimentation
  DMP / Mon Espace Santé. Le rejeu retraite une donnée **déjà reçue et déjà
  stockée** ; il ne crée aucun nouveau flux sortant
- **Référentiels métier** : CIM-10 / LOINC / CCAM présents dans le contenu
  clinique indexé — inchangés par cette US, mais leur bonne indexation est
  précisément ce que le rejeu restaure
- **Hébergement HDS** : oui — Staging et Production de la plateforme. Point de
  vigilance : le rejeu **renvoie du contenu clinique vers OpenAI**, exactement
  comme la réception nominale. Aucune capacité nouvelle, aucun flux nouveau —
  mais un flux qui peut devenir **massif** sur un rejeu large, d'où l'exigence
  de bornage explicite
- **AIPD / impact RGPD** : **à mettre à jour** — non pour un traitement nouveau,
  mais parce que la possibilité d'un retraitement de masse a posteriori
  d'un stock de données de santé déjà reçues est un mode d'exécution non décrit
  dans l'AIPD actuelle (volumétrie et sous-traitance OpenAI)
