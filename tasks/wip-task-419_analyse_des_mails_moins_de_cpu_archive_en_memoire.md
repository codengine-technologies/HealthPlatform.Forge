# todo-task-419.md — Analyse des mails : un tiers de CPU en moins, archive IHE-XDM en mémoire, et plus de document perdu au démarrage

**Repos**: interop-cda, api-mail
**Dependencies**: — (aucune)
**Epic**: E011
**Single frontend**: true
**Priorité**: **1**. Le lot corrige une **perte définitive de contenu médical** (E3) : au démarrage d'une
réplique, des documents sont enregistrés sans corps ni HTML, et leur mail est marqué analysé. Il porte aussi
**−34 % de CPU par mail analysé**, mesuré au banc.

> **Origine.** Laboratoire CPU des 2026-10-31 et 2026-11-01, demandé par l'humain : un levier à la fois, un tir de
> 16 médecins pendant 8 min après chaque changement, gardé seulement si le gain est mesuré, sans régression.
> Rapport : `Docs/audits/api-mail-labo-cpu-enrichissement-20261031.md`, précédé de la phase 0
> (`Docs/audits/api-mail-loadtest-phase0-cout-cpu-enrichissement-20261031.md`).
>
> **Une seule task, par décision humaine du 2026-11-01.** Le rapport proposait d'abord 7 tasks, une par levier. Le
> gain de chaque levier est déjà mesuré, et un cycle de forge est long : les 8 leviers passent ensemble.

## Ce qui est établi (banc, 16 médecins, 8 min, 5 réplicas)

| Indicateur | Avant | Après le laboratoire | Écart |
|---|---|---|---|
| CPU de l'API par mail analysé | 99,9 ms | 65,9 ms | −34 % |
| Débit d'analyse | 46,4 mails/s | 56,1 mails/s | +21 % |
| CPU du poste par mail | 394 ms | 262 ms | −33 % |
| CPU de Postgres par mail | 31,5 ms | 23,2 ms | −26 % |
| Lot de 10 mails, p50 / p95 | 3,45 s / 4,64 s | 2,87 s / 3,79 s | −17 % / −18 % |
| Journaux Information par mail | 30,5 | 2,4 | −92 % |
| Documents sans contenu par démarrage à froid | 4 à 5 | 0 | — |

- **Bruit** : ±1,5 % sur le CPU de l'API entre trois essais identiques.
- **Debug et Release** : l'écart mesuré est de −1,4 %, dans le bruit. Les chiffres du banc valent pour la
  production.
- **Non-régression au laboratoire** : à chaque essai, l'empreinte d'environ 1 700 mails analysés est identique,
  hors bruit préexistant des indicateurs de doublon. L'empreinte couvre le corps, le HTML, les documents, la
  biologie, les pièces jointes, les patients et les embeddings. La suite complète est verte, et chaque test ajouté a
  été vu rouge par mutation.

**Le code existe déjà**, sur les branches **locales et non poussées** `lab/cpu-enrichissement` de `Api/Mail`
(19 commits) et de `interop/interop.cda.parser` (8 commits). Il y porte la mention « Laboratoire CPU (E…) ».
`api-mail` y consomme `interop-cda` `109.0.1-lab.6` depuis un flux NuGet **local** (`nuget.config` du dépôt) : ce
montage ne doit pas sortir du poste.

## Objective

Qu'analyser un mail coûte un tiers de CPU en moins, et qu'**aucun document médical ne soit plus jamais enregistré
vide** parce que la transformation CDA → HTML échoue au démarrage. Le médecin voit la même chose qu'avant :
même corps, même rendu du document, mêmes résultats de biologie, mêmes pièces jointes, mêmes patients. Il le voit
plus vite, et un même serveur sert plus de médecins.

Aucun contrat ne change :
- pas de DTO ni de frontend ;
- pas de format d'évènement sur le relais temps réel ;
- pas de format d'archive accepté ;
- mêmes bornes et mêmes contrôles de sécurité de l'archive IHE-XDM.

### Périmètre : les 8 leviers gardés

| # | Dépôt | Changement | Gain mesuré |
|---|---|---|---|
| **E3** | interop-cda | Feuilles XSLT et ressources de localisation (`cda_asip.xsl`, `cda_l10n.xml`…) servies **depuis la mémoire** par un résolveur, au lieu d'être réécrites dans `%TEMP%/cda_xslt_html` par chaque processus et relues à chaque transformation. **Corrige la perte de contenu** : « The process cannot access the file 'cda_asip.xsl' » aux premières transformations concurrentes. | exactitude |
| E2 | interop-cda | `CdaValidator` : le CDA est lu et analysé **une fois**. Le `XmlSchemaSet` chargé pour chaque document n'était jamais utilisé, et le document était relu 3 fois. | −5,4 % |
| E8 | interop-cda | Extraction de texte PDF : **une à la fois par processus**. PdfPig 0.1.16 tient un verrou global (`OperatorToken.Lock`), et l'attente concurrente brûlait du CPU. | −2,2 % |
| **E6** | interop-cda + api-mail | **Archive IHE-XDM traitée entièrement en mémoire** : plus de zip écrit ni d'extraction sur disque. Mêmes bornes (`XdmExtractionLimits`), mêmes contrôles de chemin, même classement des échecs, mêmes messages de journal que la voie disque. | −14,5 % (poste −31 %) |
| E1 | api-mail | Journaux de suivi d'étape émis pour chaque mail : Information → Debug. Polly en `Warning`. **`[AiCall]` reste en Information** (exigence de task-385). | −3,5 % |
| E5 | api-mail | Assainissement HTML (AngleSharp) **sans observateur d'attributs** : plus d'URL construite pour chaque `src` d'iframe ou d'image, notamment les PDF en base64. | −4,3 % |
| E7a | api-mail | Écritures ciblées `ExecuteUpdateAsync` au lieu de relire la ligne entière : embedding du contenu, embedding du document, lien praticien → contact. | −2,1 % (Postgres −15 %) |
| **E4b** | api-mail | Relais SSE, **format Redis inchangé** : la réception lit l'en-tête (`Topic`, `MailboxEmail`, `Folder`), et la charge (le `MailDto` entier) n'est décodée que si un abonné local la demande. | −6,8 % (GC gen2 −20 %) |

### À finir avant la production (E6 est un prototype)

1. **Pas de registre global en mémoire.** Au laboratoire, les octets d'une archive vivent dans un registre statique
   du processus (`IheXdmMemoryScratch`), indexé par un « chemin » factice. Un lot jamais libéré y fuirait : le disque
   avait son balayage au démarrage, la mémoire n'en a pas. Les octets doivent voyager dans un **type porteur**
   (l'archive elle-même) de la réception à l'analyse, avec une durée de vie bornée par le lot.
2. **Plus de chemins factices** : `CdaParsingService` et `IheXdmProcessingService` reçoivent l'archive, pas un
   chemin à résoudre.
3. **La voie disque disparaît** si plus rien ne l'appelle : `IheXdmScratchDirectory`, son répertoire, son balayage
   au démarrage, le paramètre `inMemory`. Si elle doit rester, par exemple pour la limite de taille, le task file dit
   pourquoi. La garde existante sur le répertoire `mss-ihe-xdm` est revue en conséquence.
4. **L'empreinte mémoire est bornée.** Une archive en mémoire pèse ce qu'elle pesait sur disque, et les bornes
   d'extraction (taille totale, nombre d'entrées, taux de compression) restent appliquées **avant** de décompresser.
   Le task file note la taille maximale d'une archive acceptée, et le pic mémoire d'un lot de 10 mails.
5. **Retirer les mentions « Laboratoire CPU »** des commentaires, ou les reformuler en explication durable du
   pourquoi.

### Hors périmètre, explicitement

Ces pistes sont écartées au laboratoire, chiffres dans le rapport :
- **E4**, E7b et E9 ;
- la fusion des 4 analyses HtmlAgilityPack ;
- un seul appel d'embedding par mail ;
- les contacts traités dans le consommateur ;
- un relais SSE allégé ou conditionné à la présence d'un abonné : c'est une **décision produit** à prendre à part ;
- `[AiCall]` en Debug : décision humaine, task-385.

Restent aussi hors périmètre :
- la **détection de doublon / remplacement non déterministe** (constat 2 du rapport) : préexistante, à instruire
  dans une US dédiée ;
- toute modification de `Dtos/`, d'un frontend ou du format de l'évènement SSE.

## Definition of Done

- [ ] Build passes (0 errors) : `interop.cda.parser.sln` et `HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) sur les deux dépôts. Exception admise : les 3 tests « du jour » de l'intégration,
      rouges connus entre 00:00 et 02:00, à condition d'être rejoués verts après 02:00
- [ ] Les 8 leviers E3, E2, E8, E6, E1, E5, E7a et E4b sont portés depuis `lab/cpu-enrichissement`, et le task
      file les liste avec leurs commits d'origine. **E4, E7b et E9 n'y sont pas**, leurs commits sont annulés sur la
      branche de laboratoire
- [ ] `interop-cda` publié par sa CI dans une version normale. `api-mail` la consomme par le flux habituel :
      **aucun `nuget.config` local, aucune version `-lab`** dans `Directory.Packages.props` ni dans les
      `packages.lock.json`
- [ ] E6 finalisé : les 5 points de « À finir avant la production » sont traités, et le task file dit comment pour
      chacun, avec la taille maximale d'archive et le pic mémoire d'un lot
- [ ] **Test d'intégration de bout en bout, `POST /api/v1/mail/folders/{foldername}/emails/enrich/sync`, démarrage
      à froid** : N mails porteurs d'un IHE_XDM.ZIP sont analysés en parallèle sur un processus neuf. Chaque document
      enregistré a un `HtmlBody` et un `Body` **non vides**, lus en base ou dans la réponse.
      - Vu rouge par mutation (règle 1b) : réinjecter l'écriture disque des ressources XSLT par processus.
      - Si la concurrence ne peut pas être reproduite de façon fiable dans le fixture, le task file le dit, et la
        preuve passe par le test d'`interop-cda` qui transforme en parallèle, vu rouge de la même façon.
- [ ] **Test d'intégration de bout en bout, même route, archive IHE-XDM traitée en mémoire** :
      - documents, texte, HTML, pièces jointes **et PDF associé au CDA** (fichier voisin, ECO.2.1.1) identiques à ceux
        de la voie disque ;
      - **aucun fichier** écrit dans le répertoire temporaire pendant l'analyse ;
      - vu rouge par mutation : la voie mémoire perd les PDF associés ;
      - une archive illisible ou hors bornes est classée et journalisée comme avant, cas d'échec compris.
- [ ] Tests unitaires conservés depuis le laboratoire et verts :
      - `InMemoryXsltResolverTests`, `XdmLoadInMemoryTests`, `PdfTextExtractionConcurrencyTests` (interop-cda) ;
      - `CdaParsingInMemoryEquivalenceTests`, dont le cas avec PDF associé fabriqué ;
      - `HtmlBodySanitizerParsingTests`, `SseBackplaneEnvelopeTests` ;
      - `MedicalDocumentRepositoryIntegrationTests` (Postgres).
- [ ] **E4b, compatibilité du format** : une enveloppe publiée par une réplique **non mise à jour** est lue par une
      réplique mise à jour, et inversement. Un abonné reçoit une charge **identique octet pour octet** à celle
      d'avant. Si le fixture d'intégration dispose de Redis, ce test passe par le vrai Redis.
- [ ] **E7a** : les trois `ExecuteUpdateAsync` sont prouvés sur Postgres, avec relecture dans un contexte neuf.
      L'`UPDATE` ne touche que la colonne visée, vu rouge par mutation
- [ ] **E1** : le task file liste chaque journal passé en Debug.
      - `[AiCall]` reste en Information, prouvé par un test.
      - Les journaux d'échec et d'avertissement ne changent pas de niveau.
- [ ] Aucune donnée de santé en clair dans les journaux : aucun journal ajouté ou modifié ne porte de contenu CDA,
      d'INS, de NIR, de nom de patient ni de contenu de mail. Les chemins d'archive journalisés restent techniques
- [ ] Contrat inchangé : aucun fichier de `Dtos/` modifié, aucun frontend touché, format de l'enveloppe SSE
      inchangé, prouvé par `Serialize_KeepsTheEnvelopeFormat_HeaderBeforePayload`
- [ ] Les branches `lab/*` ne sont **pas** poussées. Elles restent la référence locale, et l'humain les supprime
      après le merge
- [ ] **Tir de contrôle après merge** (banc requis, crédit OpenAI rechargé) : le protocole du rapport, 16 médecins
      pendant 8 min, fenêtre [t+75 s, t+435 s]. CPU de l'API par mail et débit comparés à la référence B0 (99,9 ms,
      46,4 mails/s), résultat ajouté au rapport.
      - **Aucun seuil n'est un critère de DOD** : la task se merge sur sa justesse, et la mesure dit ce qu'elle
        valait.
      - Si le banc n'est pas disponible dans le cycle, noter « mesure en attente » dans le task file.

## Manual Test Plan

1. **Lancer le backend** : `cd Api/Mail && dotnet run --project src/AppHost`, profil par défaut, ou
   `https-load-test` (skill de banc) pour un tenant hydraté.
2. **Démarrage à froid** : arrêter puis relancer l'AppHost, puis analyser **tout de suite** un dossier d'au moins
   10 mails porteurs d'un IHE_XDM.ZIP. Utiliser `client-blazor` ou `client-mobile` (ouverture du dossier), ou
   `POST /api/v1/mail/folders/INBOX/emails/enrich/sync`. Le kit ANS de la boîte de test convient.
3. **Rendu des documents** : ouvrir chaque mail analysé. Le document s'affiche avec son rendu HTML et son texte ;
   aucun document n'est vide.
4. **Journaux d'échec** : dans Seq (`seq-local`), aucune ligne « The process cannot access the file » ni
   `cda_asip.xsl` depuis le démarrage.
5. **Archive en mémoire** : aucun fichier n'apparaît sous `%TEMP%` dans `cda_xslt_html` ni dans le répertoire de
   travail IHE-XDM pendant l'analyse.
6. **PDF associé** : un mail dont l'archive porte un PDF à côté du CDA montre ce PDF en pièce du document, comme
   avant.
7. **Biologie et patients** : les résultats de biologie d'un CR-BIO s'affichent comme avant, et le patient du
   document est rattaché comme avant.
8. **Temps réel** : client ouvert sur la boîte, déposer un nouveau mail. La notification arrive et le mail
   apparaît dans la liste sans recharger la page, comme avant.
9. **Journaux** : dans Seq, une analyse de 10 mails ne produit plus que quelques lignes Information par mail, dont
   `[AiCall]`. Les mêmes étapes sont visibles en Debug.
10. **Mesure** (si le banc est disponible) : le protocole du rapport, section « Protocole », comparé à la référence
    B0.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur. Optimisation interne et correctif de fiabilité, sans exigence fonctionnelle
  nouvelle
- **Exigences DSR honorées** : non applicable. Aucun comportement visible du PS ne change, hormis la fin d'une
  perte de document (fiabilité de la réception MSSanté)
- **INS** : non applicable. Aucun trait d'identité n'est manipulé différemment ; l'extraction du patient du CDA
  reste celle d'`interop-cda`, à l'identique (empreinte « patients » vérifiée au laboratoire)
- **Authentification PS** : inchangée (PSC / e-CPS). La route d'analyse garde ses garde-fous
- **Habilitations** : inchangées. Même base par boîte, même verdict de l'opérateur (règle 14). Aucune action sur
  une boîte n'est ajoutée ni modifiée
- **Interop CI-SIS** : CDA r2 reçu en IHE-XDM (volet de transport MSSanté, ECO.2.1.1). Le CDA transite toujours par
  `interop-cda` et sa validation ; seule la lecture change (en mémoire, une seule analyse). Le rendu HTML reste
  celui de la feuille de style ANS (`cda_asip.xsl`), servie depuis la mémoire
- **Tracé PGSSI-S** : inchangé. Aucun évènement de traçabilité n'est retiré ; seuls des journaux techniques de
  suivi d'étape passent en Debug. `[AiCall]` reste en Information (task-385)
- **Consentement patient** : non applicable
- **Référentiels métier** : LOINC (codes de document et de biologie) lus à l'identique, aucun changement
- **Hébergement HDS** : oui, environnement inchangé. Effet positif : les archives IHE-XDM, qui sont des données de
  santé, ne sont plus écrites en clair dans le répertoire temporaire du serveur
- **AIPD / impact RGPD** : inchangé, aucun traitement nouveau. À noter dans l'AIPD si elle décrit les fichiers
  temporaires : il n'y a plus de copie disque transitoire des archives

## Branches
- `interop-cda` (pushed) : feat/task-419-analyse-des-mails-moins-de-cpu-archive — https://github.com/codengine-technologies/interop.cda.parser/tree/feat/task-419-analyse-des-mails-moins-de-cpu-archive
- `api-mail` (pushed) : feat/task-419-analyse-des-mails-moins-de-cpu-archive — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-419-analyse-des-mails-moins-de-cpu-archive
- Référence du code à porter (locale, **non poussée**, ne jamais pousser) : `lab/cpu-enrichissement` dans `Api/Mail` et dans `interop/interop.cda.parser`

## Timings

*(généré par `tools/timing/report.sh --task task-419 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 20 s | — | — | — | — |
| /develop | ok | 44 min 26 s | 10 (47 s) | 22 (15 min 48 s) | — | interop-cda 1B/4T, api-mail 9B/18T |
| **Total cycle** | | **44 min 46 s** | **10 (47 s)** | **22 (15 min 48 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : nuget-wait ×1 (35 s)

## Develop log

- **Repos touchés** : `interop-cda`, `api-mail`. Aucun DTO touché.
- **Interop publié** : `Interop.Cda.Parser` 109.0.0 → **117.0.0** (CI run 117, succès). `api-mail` le consomme par le flux habituel : `nuget.config` inchangé, aucune version `-lab` (`Directory.Packages.props` et les 11 `packages.lock.json`).
- **Commits** :
  - interop-cda : `8e55fab` perf(cda) (E3, E2, E6, E8, portés de `lab/cpu-enrichissement` : `e723132`, `4212b49`, `b1005bc`, `2b35544`, `e87aabb`, `7cf008e`, `0a04416`) · `3a5e89d` test(cda) démarrage à froid
  - api-mail : `6181d502` chore(deps) bump 117.0.0 · `688208b9` perf(mail) (E1 `515b6a96`, E5 `ef4d4940`, E7a `257e6e9c`, E6 `c9526856`/`f13b977b`/`a976023b`, E4b `7a4ef5e0`, finition E6) · `56cfc5c3` refactor(mail) simplify pass
  - **Exclus** : E4 (`408a90c5`, annulé par `a1062ea8`), E7b (`4fa36f08` / `91a3eef7`), E9 (`b55d4499` / `9fb734fb`). La reprise s'est faite par l'état net de la branche de laboratoire : les commits annulés n'y laissent rien.
  - Les branches `lab/*` ne sont **pas** poussées.

### E6 — les 5 points « à finir avant la production »

1. **Plus de registre global** : le registre statique `IheXdmMemoryScratch` est supprimé. Les octets vivent dans le lot (`IheXdmScratchSet.Files`, des `IheXdmScratchFile(Name, Content)`), qui voyage dans `FetchedMail` jusqu'à la persistance. Un lot jamais libéré est récupéré par le ramasse-miettes avec son propriétaire : rien ne peut fuir hors de lui.
2. **Plus de chemins factices** : `ProcessIheXdmZips(IReadOnlyList<IheXdmScratchFile>)`, `IEmailBuildingService.BuildMailDtoAsync(…, IReadOnlyList<IheXdmScratchFile>, …)`, et `ICdaParsingService.ParseIheXdmZip(byte[] archive, string archiveName, …)`. `MssanteHeaderService` analyse aussi les octets : il n'écrit plus de fichier temporaire.
   - La surcharge par chemin reste sur le service, pour les archives réellement sur disque. Elle sert de référence « voie disque » aux tests d'équivalence.
3. **La voie disque disparaît** : `CreateFile` sur disque, la recréation du répertoire (task-293), le paramètre `inMemory` et `NewSet()` sont retirés.
   - `IheXdmScratchDirectory` ne garde que **le balayage au démarrage** de l'ancien `%TEMP%/mss-ihe-xdm`. **Pourquoi il reste** : une instance déjà déployée a pu y laisser, après un arrêt brutal, des archives et des répertoires d'extraction en clair, et plus rien d'autre ne les supprimerait. Il pourra partir une version plus tard.
   - La garde « scratch mss-ihe-xdm » (mémoire du banc) devient sans objet : un répertoire supprimé ne casse plus rien.
4. **Empreinte mémoire** :
   - **Bornes** : `XdmExtractionLimits`, inchangées et appliquées avant décompression. Au plus 1 000 entrées et **256 Mio décompressés** par archive, avec un taux de compression de 100 au plus.
   - **Taille maximale d'une archive** : aucune limite propre côté réception. L'archive pèse ce que pèse la pièce jointe IMAP, comme sur disque avant. La limite d'envoi de la plateforme est de 10 Mio (`MailOptions.MaxAttachmentSizeBytes`).
   - **Pic d'un lot de 10 mails** : borne de code = somme des archives compressées du lot, tenues jusqu'à la persistance, plus une archive décompressée par analyse en cours.
   - **Mesure en attente** : le pic n'a pas été mesuré au banc. Le crédit OpenAI est épuisé, aucun tir complet n'est possible, et ce sera au tir de contrôle.
   - Piste notée, non appliquée faute de mesure : libérer le lot juste après `BuildMailDtoAsync` au lieu de la fin de la phase B.
5. **Mentions « Laboratoire CPU »** : retirées ou reformulées en `task-419 — …` dans les deux dépôts.

### E1 — journaux passés de Information à Debug

- `MailController` « 🔄 Enriching » ; `MailEnrichmentNotifier` ×3 ; `AddNewMailConsumer` ×4 (traitement, fin, embedding) ; `CreatePatientContactConsumer`, `CreatePractitionerContactConsumer` ; `CdaParsingService` (« Parsing completed », valeur de biologie manquante) ; `EnrichedMailPersistence` (SKIP) ; `PatientContactPublisher` ×2, `PatientContactService` ×4, `PractitionerContactPublisher` ×3, `PractitionerContactService` ×4 ; `ImapLockScope` ×2 (verrou acquis/libéré) ; `XDM` et `SubmissionSet` côté `interop-cda`. `"Polly": "Warning"` dans `appsettings.json` et `appsettings.Production.json`.
- **`[AiCall]` reste en Information** : `tests/mss.mail.api.tests/Extensions/MeteredAiServicesTests.cs:174` l'exige toujours, et passe.
- **Aucun niveau changé** sur les journaux d'échec ou d'avertissement. La lenteur d'un verrou reste en Warning.
- **Données de santé** : la ligne « valeur de biologie manquante » portait le nom de l'examen et sa section, du contenu CDA. Elle n'en porte plus : « A biology result without value is skipped ».

### Tests et preuves du rouge (règle 1b)

| Comportement | Test | Preuve du rouge |
|---|---|---|
| E3 — aucune transformation ne casse au démarrage à froid sous un voisin qui réécrit `cda_xslt_html` | `interop-cda` : `CdaHtmlConcurrentStartupTests` (20 démarrages à froid × 8 transformations en parallèle) | Mutation : ancien chargement disque réinjecté → **rouge 3 fois sur 3**, « Access to the path 'cda_asip.xsl' is denied », la famille d'erreur du banc |
| E3 — reproduit au niveau de la route `enrich/sync` | **non reproductible de façon fiable dans le fixture** : le cache de la feuille compilée est statique au processus, déjà chaud au moment des tests d'intégration | La preuve passe par le test d'`interop-cda` ci-dessus, comme la DOD le prévoit |
| E6 — `POST /api/v1/mail/folders/{folder}/emails/enrich/sync` : mêmes documents que la voie disque, PDF associé compris (contenu exact relu en base), corps et HTML non vides, aucun fichier de travail écrit | `XdmInMemoryAnalysisEndToEndTests` (Dovecot + Postgres réels) | Mutation : le lot ne retient plus le fichier écrit → **rouge** (« Collections differ », 0 document) |
| E6 — équivalence disque / mémoire sur les 7 archives du corpus + PDF associé fabriqué | `CdaParsingInMemoryEquivalenceTests` | Laboratoire : mutation « la voie mémoire perd les PDF associés » → rouge |
| E6 — une panne d'hôte laisse le mail à traiter, 503, puis analysé une fois rétabli | `ArchiveAnalysisMarkerEndToEndTests` (injection : lecture d'archive en échec ; l'effacement disque n'existe plus), `EnrichmentScratchFailureTests` (lecture IMAP interrompue) | Tests existants de task-293/333 conservés, panne réinjectée sous sa forme encore possible |
| E4b — une enveloppe d'une réplique **non mise à jour** est livrée inchangée à l'abonné, sur vrai Redis | `MultiReplicaRedisIntegrationTests.EmailsEnriched_PublishedByAReplicaOnThePreviousVersion_ReachesTheClientUnchanged` (+ contrat octet pour octet existant) | Mutation : dossier perdu à la lecture de l'en-tête → **rouge** (2 tests) |
| E4b — format inchangé (en-tête avant charge) | `SseBackplaneEnvelopeTests.Serialize_KeepsTheEnvelopeFormat_HeaderBeforePayload` | Laboratoire : charge décodée immédiatement → rouge |
| E7a — trois `ExecuteUpdateAsync`, relus dans un contexte neuf | `MedicalDocumentRepositoryIntegrationTests`, `MailRepositoryIntegrationTests` (Postgres) | Laboratoire : l'`UPDATE` touche une autre colonne → rouge |
| E5 — l'analyseur n'a plus d'observateur d'attributs | `HtmlBodySanitizerParsingTests` | Rouge naturel au laboratoire (un premier essai le laissait) |
| E8 — une extraction PDF à la fois | `PdfTextExtractionConcurrencyTests` (interop-cda) | — |

- **Build / tests locaux** :
  - interop-cda : **518** verts (6 ignorés) ;
  - api-mail : domaine 202, infrastructure 699, API 1 315, application **3 952**, intégration **1 095** (16 ignorés), tout vert, avant et après la passe qualité.
  - Application −4 par rapport au laboratoire : les tests du répertoire disque sont retirés (recréation, droits, fichier encore ouvert, HPRIM disparu du disque) et un test du lot libéré est ajouté.
- **Passe qualité (/simplify)** :
  - **Appliquée et commitée** : api-mail, 20 fichiers (`56cfc5c3`) ; re-validation build + suites complètes au vert.
  - **Écartées, notées pour la revue** :
    - retirer la surcharge par chemin d'`ICdaParsingService` : elle reste la référence « voie disque » des tests ;
    - remplacer le flux `EntryStream` par un `Add(kind, bytes)` typé : la classification par extension date de task-389, et un fichier lu en partie rejoignait déjà le lot avant ;
    - refondre `SseBackplaneMessage` en classe : la forme mesurée au laboratoire est gardée ;
    - dimensionner le tampon d'archive à l'avance : le laboratoire a mesuré 0 % de gain sur des copies évitées du tas des gros objets (E9).
  - **Sans objet** (porteur de contrat) : interop-cda.
- **Contrôles mécaniques §Q 2b** : deux S125 trouvés et corrigés avant le push (`conventions/csharp.md`, Occurrences 23 → 24). Rien d'autre.
- **Taille de PR** : la PR api-mail compte ~84 fichiers, au-delà des ~30 visés. Le détail : 11 `packages.lock.json`, ~45 fichiers de tests adaptés au passage des chemins aux octets, le reste du code de production. Le découpage en une seule task est une décision humaine du 2026-11-01.
- **Hors task, mis de côté** : deux lignes d'index de rapports de tir (`tests/loadtest-k6/reports/INDEX.md`, `POSTGRES-INDEX.md`), écrites par les essais du laboratoire. Elles sont dans `git stash` d'`Api/Mail` (« task-419: index de rapports du labo (hors task) »).
- **DOD auto-contrôlée** :
  - le tir de contrôle après merge est **en attente** (banc, crédit OpenAI) ;
  - tous les autres items sont vérifiés.
- **Étape suivante** : `/sonar task-419`.
