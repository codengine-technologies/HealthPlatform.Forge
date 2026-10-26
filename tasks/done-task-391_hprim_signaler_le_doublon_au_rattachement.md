# todo-task-391.md — Rattacher un résultat HPRIM déjà présent dans le dossier du patient : signal doublon

**Repos**: api-mail
**Dependencies**: task-389 (le document HPRIM existe, dans la file « à intégrer »), task-390 (résultats structurés)
**Epic**: E009
**Single frontend**: true
**Priorité**: **3** — un laboratoire qui renvoie le même résultat (renvoi, double adressage) produit deux documents identiques. Une fois rattachés au même patient, ils restent côte à côte sans que rien ne le signale.

> **Origine.** Séance `/po` du 2026-10-23 (parsing HPRIM), suite de task-389 et task-390.
> **Périmètre réduit par l'humain le 2026-10-26** : cette US ne livre que le **signal doublon**.
> - Le remplacement d'un résultat partiel par le complété est **abandonné** : le partiel et le complété restent tous deux visibles, le partiel marqué « partiel » (task-390, task-392).
> - La suggestion de patient par traits existe déjà (task-012, task-137) et n'est pas modifiée.
>
> **US backend seule (justification)** : le bandeau doublon et la décision du médecin existent déjà dans le mobile et weda2 (task-013). Ils s'affichent pour un document HPRIM sans changement côté client. Le signal est prouvé par test d'intégration ; aucun parcours médecin nouveau, donc pas de scénario e2e (arbitrage du 2026-10-26).

## Ce qui est établi

- **Rattachement existant** (task-012, task-137, task-331) : `POST medical-documents/{id}/attach-patient`. Le médecin choisit une fiche existante, jamais créée depuis le rattachement.
- **Signal doublon existant** (task-013) :
  - un document porte `DuplicateOfId` (`IsDuplicate` dans la réponse) ;
  - le client affiche un bandeau, et le médecin garde ou écarte (`POST medical-documents/{id}/duplicate-decision`) ;
  - un doublon non tranché reste visible : rien n'est masqué sans le médecin.
- **Aucune détection à la réception pour un document sans INS** (task-193, décision 6 de task-389) : un HPRIM n'a jamais d'INS, il n'est rapproché de rien à son arrivée. Le rapprochement se fait **au rattachement**, contre le seul dossier du patient choisi par le médecin.
- **Un fichier `.hpm` peut porter plusieurs résultats**, donc plusieurs patients (task-389 : un document par résultat). Un même résultat peut être renvoyé seul ou regroupé avec d'autres, et dans un autre encodage.

## Décisions actées (humain, 2026-10-26)

1. **Périmètre** : seul le signal doublon. Ni remplacement du partiel, ni changement de la suggestion de patient.
2. **Reconnaissance du « même résultat »** : par une **empreinte de son contenu**, proposée par l'humain et précisée en séance.
   - Une empreinte **par résultat**, pas par fichier : en-tête et texte du résultat.
   - Calculée sur le contenu **décodé**, aux fins de ligne normalisées : le même résultat renvoyé dans un autre encodage ou regroupé autrement garde la même empreinte.
   - Algorithme **SHA-256** (MD5 est signalé comme faible par l'outillage qualité, sans gain ici).
   - Elle est conservée avec le document. Le n° de dossier du laboratoire n'est pas conservé.
3. **Backend seul**, sans scénario e2e.

## Objective

Quand le médecin rattache un résultat HPRIM à un patient dont le dossier contient déjà le même résultat, le document rattaché porte le signal doublon existant. Le médecin garde ou écarte, comme pour un CDA.

### Règles métier

- **Même résultat** = même empreinte de contenu (décision 2).
- **Au rattachement seulement**, et **seulement contre le dossier du patient choisi**. Il porte sur les documents HPRIM déjà rattachés à ce patient. Un document d'un autre patient, ou encore à intégrer, n'est jamais comparé ni touché.
- **Le document rattaché en second** porte le signal doublon et désigne le premier. Le premier est inchangé.
- **Rien n'est masqué automatiquement** : le doublon reste visible jusqu'à la décision du médecin, avec le bandeau et les choix existants (task-013).
- **Résultats différents** (une valeur, une ligne ou un statut change, par exemple le partiel et son complété) : empreintes différentes, aucun signal. Les deux restent visibles.
- **Détacher** le premier document laisse le second visible ; le signal suit les règles existantes de task-013.
- **Documents HPRIM reçus avant cette US** (sans empreinte) : ils ne sont rapprochés de rien.
- **BAL déléguée** (règle 14) : un document délégué n'est jamais rattachable (task-398). Aucune empreinte n'est conservée chez le délégataire, rien n'est persisté.

## Definition of Done

- [ ] Build et tests verts : api-mail
- [ ] Empreinte SHA-256 du contenu décodé du résultat (en-tête et texte, fins de ligne normalisées), conservée avec le document HPRIM. Migration de la base mail : colonne nullable, sans effet sur les documents existants
- [ ] ≥ 1 test unitaire par règle d'empreinte :
  - même résultat → même empreinte, y compris dans un autre encodage, avec d'autres fins de ligne, ou regroupé dans un fichier à plusieurs résultats ;
  - une valeur ou un statut différent → empreinte différente ;
  - deux résultats d'un même fichier → deux empreintes
- [ ] Test d'intégration de bout en bout (règle 1b) pour `POST attach-patient` :
  - **nominal** : le même HPRIM est reçu deux fois, et les deux documents sont rattachés au même patient. Le second porte le signal doublon (`IsDuplicate`, `DuplicateOfId` = le premier), lu dans la réponse réelle du contenu du message et des documents du patient. Le premier n'en porte pas, et aucun n'est masqué ;
  - **cas d'échec** : un HPRIM dont une valeur diffère n'est pas signalé ;
  - **autre patient** : le même résultat rattaché à deux patients différents n'est pas signalé ;
  - vu rouge
- [ ] Test d'intégration : la décision du médecin sur le doublon HPRIM (`duplicate-decision`) suit le comportement existant de task-013
- [ ] **BAL déléguée — test d'intégration** (banc de délégation de task-397) : un HPRIM délégué n'expose aucun identifiant rattachable, et la base du délégataire ne contient aucun document ni empreinte pour ce message ; vu rouge (règle 1b)
- [ ] Aucune donnée de santé en clair dans les journaux : ni trait patient, ni valeur, ni empreinte

## Manual Test Plan

Lancer l'AppHost, puis le mobile (`cd Client/Mobile && npm start`) et weda2. Se connecter en Cyril par PSC.
Messages de test : le même HPRIM synthétique déposé **deux fois** dans la Réception de Cyril (`.eml` comme pour task-389), puis une variante dont une valeur diffère.

1. Rattacher le premier document à une fiche existante : aucun bandeau.
2. Rattacher le second à la **même** fiche : le bandeau doublon s'affiche ; « garder » et « écarter » fonctionnent comme pour un CDA.
3. Rattacher la variante (valeur différente) à la même fiche : aucun bandeau.
4. Rattacher le même résultat à une **autre** fiche : aucun bandeau.
5. Seq : aucun trait patient, aucune valeur, aucune empreinte.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : biologie médicale (réception en médecine de ville)
- **Vague Ségur** : hors Ségur — HPRIM, format historique hors CI-SIS
- **Exigences DSR honorées** : identito-vigilance — aucun rapprochement avant le choix explicite du patient par le médecin ; rapprochement limité au dossier de ce patient ; rien n'est masqué sans décision du médecin
- **INS** : non applicable — le HPRIM ne porte pas d'INS ; l'empreinte ne sert jamais à identifier un patient
- **Authentification PS** : inchangée — PSC / e-CPS de la session de messagerie
- **Habilitations** : documents de la boîte du médecin. BAL déléguée : aucun rattachement possible (règle 14, task-398)
- **Interop CI-SIS** : non applicable — HPRIM Santé
- **Tracé PGSSI-S** : rattachement déjà tracé (task-012) ; la décision sur un doublon suit le tracé existant (task-013) ; aucun nouvel évènement
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangée — l'empreinte est dérivée d'un compte rendu déjà reçu et conservé avec lui ; elle n'est ni exposée ni journalisée

## Branches
- `api-mail` (pushed) : feat/task-391-hprim-signaler-le-doublon-au — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-391-hprim-signaler-le-doublon-au
- Run `/forge` `forge-20261026-391-392` (staging `forge/staging-task-391-392-20261026`)

## Timings

*(généré par `tools/timing/report.sh --task task-391 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 4.9 s | — | — | — | — |
| /develop | ok | 55 min 38 s | 12 (1 min 35 s) | 13 (29 min 01 s) | — | api-mail 12B/13T, reprise revue : changement de patient, cache des liés, 53300 |
| /sonar | ok | 8 min 30 s | 2 (43 s) | 10 (13 min 28 s) | 4 (1 min 29 s) | 1 itération(s), api-mail 2B/10T, re-scan 3ef5617c : QG OK, 0 issue |
| /lint-angular | skipped | 0.5 s | — | — | — | repo non touché |
| /lint-mobile | skipped | 0.5 s | — | — | — | repo non touché |
| /e2e | ok | 0.4 s | — | — | — | e2e ×6 (32 min 08 s), 2 voies vertes sur 6816d504, porte 0 |
| /review | ok | 0.5 s | — | — | — | APPROVED 3e passe, PR #318 |
| /tech-writer | ok | 0.6 s | — | — | — | — |
| **Total cycle** | | **1 h 04 min** | **14 (2 min 18 s)** | **23 (42 min 29 s)** | **4 (1 min 29 s)** | |

## Develop log

> Journal de progression (point de reprise en cas de compaction).

- **Repos touché** : `api-mail` seul. Aucun contrat changé : `IsDuplicate` et `DuplicateOfId` existent déjà (task-013).

**Conception** :
- `src/Application/Hprim/HprimFingerprint.cs` (pur) : SHA-256 en hexadécimal minuscule du contenu **décodé** du document HPRIM. Le contenu canonique, séparé par lignes, comprend :
  - laboratoire, expéditeur, nom, prénom, date de naissance, date du résultat ;
  - le texte, aux fins de ligne normalisées et aux lignes rognées ;
  - chaque résultat structuré (libellé, code, valeurs, unités, bornes, indicateur, statut).

  `null` pour tout autre format.
  - **Écart avec la décision 2** (« en-tête et texte du résultat ») : l'empreinte porte sur ce qui est **conservé** du document, pas sur les 12 lignes brutes de l'en-tête. L'adresse, le NIS et le n° de dossier ne sont pas gardés (task-389). Deux résultats identiques en tout sauf le n° de dossier auraient la même empreinte : même patient, même laboratoire, même jour, mêmes valeurs. C'est sans conséquence clinique, et c'est signalé au HAG.
  - Les résultats structurés entrent dans l'empreinte : task-392 retirera les lignes `RES|` du texte, et l'empreinte restera alors fidèle aux valeurs.
- **Persistance** : colonne `MailMedicalDocuments.ContentFingerprint`, `varchar(64) NULL`. Elle est posée par `MailRepository.CreateMedicalDocumentEntity`, donc par le circuit existant, pour les deux chemins d'ingestion.
  - Migration FluentMigrator `20261026130000_AddMedicalDocumentContentFingerprint` : la colonne, plus l'index **partiel** `IX_MailMedicalDocuments_PatientId_ContentFingerprint` (`WHERE "ContentFingerprint" IS NOT NULL`), avec sa descente. Il est déclaré aussi dans `MailDataContext`.
  - La colonne est générique (sans référence au HPRIM) : un autre format pourra la remplir sans migration.
- **Rattachement** (`PatientRepository.AttachDocumentToPatientAsync`) : si le document a une empreinte et pas encore de signal, on cherche dans `ActiveDocumentsForPatient` (le dossier du patient **choisi**, la requête existante) un autre document de même empreinte. On prend le plus ancien. `DuplicateOfId` le désigne, avec un verdict en attente. Rien n'est cherché à la réception (task-193).
- **Détachement** (`DetachDocumentFromPatientAsync`) : pour un document à empreinte, le lien de même contenu ne vaut que dans le dossier où il a été posé.
  - Le document détaché perd son signal.
  - Ceux qui le désignaient (et qui ont une empreinte) le perdent aussi et **redeviennent visibles**.
  - Les liens doublons du CDA ne sont jamais touchés.
- **Sémantique de task-013, réutilisée telle quelle** : un doublon en attente quitte le **dossier** du patient (l'original y reste), mais reste visible dans **son message**, avec son bandeau, jusqu'à la décision du médecin.
  - La task disait « rien n'est masqué » : c'est vrai au sens où aucun contenu ne disparaît, puisque l'original au même contenu reste au dossier. En revanche, le document doublon lui-même n'apparaît pas deux fois au dossier.
  - **Point signalé au HAG** : c'est le comportement existant du CDA, que la task demandait de réutiliser.
- **Harnais de tests** : le serveur des cas d'usage HPRIM est extrait dans `UseCases/HprimServer.cs`, partagé par `HprimStructuredResultsEndToEndTests` et le nouveau test. Cela évite une neuvième copie du harnais (relevée par la passe §Q de task-390). Il gagne le détachement, la décision doublon, les documents du patient et la lecture de l'empreinte.

**Tests et preuves** :
- **Unitaires** (`HprimFingerprintTests`, 10 cas) :
  - format SHA-256 hexadécimal ;
  - même résultat → même empreinte, y compris en 1252, en 850, avec des fins de ligne Unix, ou regroupé avec un autre patient ;
  - autre valeur, autre statut ou autre patient → autre empreinte ;
  - autre format → pas d'empreinte.
- **Intégration (règle 1b)** : `HprimDuplicateOnAttachEndToEndTests`, 6 tests. Le message passe par Dovecot, `enrich/sync` et la vraie route `attach-patient`, et le signal est lu dans les réponses réelles de `emails/content` et `patients/{id}/documents`.
  - **nominal** : le second porte `IsDuplicate`, et son `DuplicateOfId` désigne le premier. Le premier n'est pas signalé, le dossier montre l'original une fois, et les deux empreintes sont égales ;
  - une valeur différente → aucun signal, deux documents au dossier ;
  - deux patients → aucun signal ;
  - autre encodage (1252) et regroupé avec un autre patient → signalé ;
  - la décision « pas un doublon » fait entrer le document au dossier (prémisse affirmée) ;
  - détacher le premier rend le second visible au dossier, sans signal (prémisse affirmée).
- **Migration** : `MedicalDocumentContentFingerprintMigrationTests`, colonne nullable sans défaut de 64 caractères et index partiel ; descente puis remontée.
- **BAL déléguée** : `DelegationEndToEndTests.ADelegatedHprim_…` étendu. `attach-patient` sur le document délégué (identifiant vide) répond **404**, et la base du délégataire n'a aucune empreinte. La protection est **structurelle** (aucune ligne, donc aucun identifiant) : aucune mutation réaliste ne la rend rouge, et c'est dit au HAG.
- **Rouge par mutation** (fichier restauré par copie) :

  | # | Mutation | Tests rouges |
  |---|---|---|
  | MA | aucun signal posé au rattachement | nominal, autre encodage regroupé |
  | ME | aucune empreinte enregistrée | nominal, autre encodage regroupé |
  | MF | désigner tout document du dossier, sans comparer l'empreinte | valeur différente |
  | MD | le détachement garde les liens | détacher le premier |
- **Non-régression** : `PatientFolderEndToEndTests` (rattachement, détachement, dossier) et `HprimStructuredResultsEndToEndTests` (sur le harnais extrait) sont verts.

### Passe qualité §Q (`/simplify`, 4 relectures : réutilisation, simplification, efficacité, altitude)

**Appliqué** :
- `HprimReceptionEndToEndTests` passe lui aussi sur `HprimServer`. Sa copie du harnais disparaît (≈ 100 lignes) ; le serveur gagne `MessageBody`, `UnattachedHprimDocumentsAsync` et `AttachmentContentAsync`.
- Les gestes des tests de doublon (`ReceiveAsync`, `DocumentAsync`) deviennent des méthodes de `HprimServer`, et `StartAsync` est direct.
- `HprimFingerprint` utilise `ReplaceLineEndings("\n")`.
- `FlagSameContentInFolderAsync` n'écrit les drapeaux du doublon que si un original est trouvé.
- `IndexFilter` de la migration se construit sur `Column`, une seule source pour le nom.
- Le test délégué perd une assertion morte (« 0 empreinte » juste après « 0 document »).

**Écarté** :
- **Helper partagé des tests de migration** (`CreateEmptyDatabase`, `Runner`) : 6 copies, motif antérieur, hors du diff.
- **`OpenPractitionerBase` commun aux tests de cas d'usage** : 8 copies antérieures.
- **`ExecuteUpdateAsync` au détachement** : gain marginal pour un geste rare touchant zéro ou une ligne liée.
- **`MedicalDocumentFingerprint.Of` générique** : à faire quand un deuxième format aura une empreinte.
- **Colonne de provenance du lien doublon** (CDA ou empreinte) : non justifiée tant que le CDA n'a pas d'empreinte.
- **L'efficacité** confirme que l'index partiel sert la recherche du rattachement, et que le chemin chaud non HPRIM est inchangé.

### Reprise après la 1ʳᵉ revue de `/review` (CHANGES REQUESTED)

**❌ 1 — un changement de patient gardait le lien doublon.**
- `attach-patient` peut déplacer un document d'un patient A vers B (task-331). Le lien posé dans le dossier de A survivait :
  - **doublon déplacé** : il restait exclu du dossier de B, et son bandeau désignait le document d'un autre patient ;
  - **original déplacé** : le doublon resté chez A restait masqué, et A n'avait plus aucun exemplaire du résultat.
- **Correction** : au changement de patient, `ClearSameContentLinksAsync` retire les liens du dossier quitté, puis `FlagSameContentInFolderAsync` cherche dans le nouveau.
- **Tests d'intégration** `MovingTheDuplicateToAnotherPatient_ClearsItsSignal` et `MovingTheOriginalToAnotherPatient_LeavesTheDuplicateVisibleInTheFirstFolder`, **vus rouges sur le code d'avant** (« Assert.False() Failure »).

**❌ 2 — la règle « autre patient » n'avait jamais été vue rouge.**
- **Mutation MO** : la recherche porte sur toute la base au lieu du dossier choisi. `TheSameHprimAttachedToTwoPatients_IsNotFlagged` passe au rouge, avec 4 autres tests.

**⚠️ adopté — cache des messages liés.**
- Détacher ou déplacer l'original retire le lien des documents qui le désignaient, mais seul le cache Redis du message du document manipulé était vidé : le bandeau doublon des autres messages survivait jusqu'à 15 minutes.
- **Correction** : `IPatientRepository.GetSameContentDuplicatesOfAsync`, lu avant le geste, puis le contrôleur vide aussi le cache de leurs messages.
- **Test unitaire de contrôleur** `DetachPatient_InvalidatesTheMailsOfTheSameContentDuplicatesToo` (le harnais d'intégration remplace le cache par un substitut). **Mutation MC** (le cache des messages liés n'est pas vidé) : rouge.

**⚠️ notés pour le HAG, non traités** :
- **Trois exemplaires** : détacher l'original rend visibles les deux autres, sans signal entre eux. Rien ne disparaît.
- **Verdict perdu** : détacher puis rattacher efface une décision « pas un doublon » ou « confirmé », et la question revient.
- **Stabilité de l'empreinte** : elle porte sur le texte et les résultats conservés.
  - task-392 retirera les lignes `RES|` du texte : un même résultat reçu avant puis après task-392 n'aura pas la même empreinte. Les résultats structurés, eux, y restent.
  - Ce n'est pas un faux positif, tout au plus un doublon non signalé.
- **Concurrence** : deux rattachements simultanés au même patient ne se voient pas : aucun signal, rien de masqué.
- **Original mis ensuite à la corbeille ou supprimé** : le doublon en attente reste exclu du dossier, comme pour un CDA (task-013, comportement existant).

- **Suites** : 7 145 + 3 tests verts (2 d'intégration, 1 de contrôleur), `PatientFolderEndToEndTests` vert.
- **53300 en suite complète** : 2 tests HPRIM et 1 test SendPaths tombaient en « too many clients ». Ils passaient isolés. Cause : les relectures du harnais (`OpenPractitionerBase`) gardaient un pool Npgsql par base d'usager, et 8 usagers de plus ont fait dépasser `max_connections`. `HprimServer` relit désormais **sans pool**. Suite d'intégration : 1 033 verts. C'est une récidive du piège de task-331 ; la mémoire est complétée (nouvelle source : les harnais de cas d'usage).

**2ᵉ passe de revue : CHANGES REQUESTED, un seul point.**
- **❌ Le signalement après un changement de patient** n'avait pas de test : un document déplacé vers un patient dont le dossier contient déjà le même contenu.
  - Test d'intégration `MovingTheDuplicateToAPatientWhoAlreadyHasTheSameContent_FlagsItThere` : le document déplacé est signalé, contre l'exemplaire du nouveau dossier.
  - **Mutation MP** (signaler seulement au premier rattachement) : rouge.
- **⚠️ Cache côté rattachement** : test unitaire `AttachPatient_InvalidatesTheMailsOfTheSameContentDuplicatesToo`. **Mutation MCA** (cache des liés non vidé au rattachement) : rouge.
- **E2E rejoué** sur `6816d504` (code de production final) : 2 voies vertes, porte 0.

## Sonar log

Analyse complète `healthplatform-api-mail` (SonarQube 9.9.8 local, `sonar.login`), sur la branche `feat/task-391-…` à `2f42b3b6`.

- **1ʳᵉ analyse** : **QG OK, 0 issue** sur le nouveau code, aucun hotspot, new coverage 95,1 %. Les cinq suites sont vertes (7 145).
- **2ᵉ analyse** (`3ef5617c`, après les reprises de revue) : **QG OK, 0 issue**, KPIs inchangés. Suites vertes (7 150).
- **Phase 1 (nouveau code)** : rien à corriger. Les consignes de `conventions/csharp.md` ont été appliquées d'emblée (CA1861 : tableaux attendus en `static readonly`). Aucune récidive.
- **Phase 2 (legacy)** : rien à faire (0 bug, 0 vulnérabilité, 0 smell sur le projet).

### KPIs qualité (baseline → final)

| Métrique | Baseline (`86e110df`, task-390) | Final (`3ef5617c`) | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | = |
| New coverage | 95,1 % | 95,1 % | = |
| New bugs / vulnérabilités / smells | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Bugs / Vulnérabilités / Smells (projet) | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Security hotspots | 0 | 0 | = |
| Coverage projet | 97,5 % | 97,5 % | = |
| Duplication | 0,4 % | 0,4 % | = |
| Ratings fiabilité / sécurité / maintenabilité | A / A / A | A / A / A | = |

## Lint log
- skipped — `client-angular` non listé dans `**Repos**:`.

## Lint mobile log
- skipped — `client-mobile` non touché par la task.

## E2E log

> ⚠️ **Quarantaine de plus de 14 jours** : E2E-COMPOSE-002 [angular], posée le 2026-10-09 (17 jours), correction due par **task-350**.
> ⚠️ **Divergence à retirer** : E2E-MAILBOX-002 [angular] (task-395). Le client weda2 est revenu à la version du catalogue ; la décision appartient à l'humain.

| Voie | Déclencheur | Résultat | Tests |
|---|---|---|---|
| mobile | api-mail touché (`6816d504`, code de production final) ; client-mobile sur `develop` à jour | ✅ verte (rejouée) | 50 verts, 0 flaky, 0 rouge, 0 quarantaine |
| angular | api-mail touché (`6816d504`) ; weda2 sur son checkout courant | ✅ verte (rejouée) | 59 verts, 0 flaky, 0 rouge, 1 quarantaine (verte) |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (inchangé : US backend, aucun parcours médecin modifié ; le bandeau doublon existant n'est pas modifié)
- Historique : première passe verte sur `2f42b3b6`. Les voies ont été **rejouées** sur `6816d504` après la reprise de revue. Le commit final `3ef5617c` ne touche que des tests.
- Porte : **code 0**, rendue par ce run
- Flaky : aucun
- Parcours touchés sans spec e2e modifié : aucun (aucun écran touché)
- Démontage : complet. Les ports 5052, 8100, 4200, 3993, 3465 et 3143 sont libres, aucun conteneur e2e ne tourne.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ · divergence (task-395) | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-DELEG-001 | 1 | headless | Voir la BAL déléguée dans sa section, repliée sous la BAL principale, et lire un compte rendu | ✅ | ✅ |
| E2E-DELEG-002 | 1 | headless | Supprimer un message délégué vers la corbeille de la délégante, puis le restaurer | ✅ | ✅ |
| E2E-DELEG-003 | 1 | headless | Dans une BAL déléguée, seuls les gestes de gestion sont proposés | ✅ | ✅ |
| E2E-DELEG-004 | 1 | headless | La délégation retirée pendant la consultation ramène à sa propre réception | ✅ | ✅ |

**Divergences temporaires ouvertes** (1) :

- E2E-MAILBOX-002 [angular] — le code weda2 de task-378 (écran de panne à l'entrée et son test) n'est pas encore livré sur la branche weda2 ; divergence décidée par l'humain le 2026-10-25 — résorbée par task-395 — **à retirer** : le client est revenu à la version du catalogue

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/318 — label `awaiting-human-merge` (head `3ef5617c`)

## Code Review Summary

**Verdict : APPROVED en 3ᵉ passe** (revue indépendante, en lecture seule).

- **1ʳᵉ passe : CHANGES REQUESTED.**
  - ❌ un document changé de patient gardait le lien doublon du dossier quitté ;
  - ❌ la règle « autre patient » n'avait jamais été vue rouge ;
  - ⚠️ adopté : cache des messages liés.
  - Corrigé par `6816d504` (tests d'intégration vus rouges, mutations MO et MC).
- **2ᵉ passe : CHANGES REQUESTED.** ❌ le signalement d'un document déplacé vers un dossier qui contient déjà le même contenu n'avait pas de test. Ajouté dans `3ef5617c` (mutation MP), avec le cache côté rattachement (MCA).
- **3ᵉ passe : APPROVED.**
- **Points renvoyés au HAG** (encadré de la PR) :
  - sémantique de task-013 pour le dossier ;
  - empreinte avant et après task-392 ;
  - trois exemplaires ;
  - verdict perdu ;
  - concurrence ;
  - original mis à la corbeille.

| Comportement atteignable par un endpoint | Test d'intégration | Rouge |
|---|---|---|
| Même résultat, même patient → signal | `TheSameHprimAttachedTwiceToTheSamePatient_…` | MA, ME |
| Autre encodage, regroupé → signal | `TheSameResultInAnotherEncodingAndRegrouped_…` | MA, ME |
| Valeur différente → aucun signal | `AnHprimWhoseValueDiffers_IsNotFlagged` | MF |
| Deux patients → aucun signal | `TheSameHprimAttachedToTwoPatients_IsNotFlagged` | MO |
| Refus du signal → au dossier | `RejectingTheDuplicateSignal_…` | prémisse (task-013) |
| Détacher l'original → doublon visible | `DetachingTheFirst_…` | MD |
| Doublon déplacé → sans signal chez le nouveau patient | `MovingTheDuplicateToAnotherPatient_…` | code d'avant |
| Original déplacé → doublon visible chez l'ancien | `MovingTheOriginalToAnotherPatient_…` | code d'avant |
| Déplacé vers un dossier au même contenu → signalé là | `MovingTheDuplicateToAPatientWhoAlreadyHasTheSameContent_…` | MP |
| BAL déléguée → 404, rien persisté | `DelegationEndToEndTests.ADelegatedHprim_…` | structurel |
| Cache des messages liés | tests de contrôleur | MC, MCA |
