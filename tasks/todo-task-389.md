# todo-task-389.md — Un résultat de laboratoire reçu au format HPRIM devient un document de biologie

**Repos**: api-mail
**Dependencies**: task-397 (lecture en mémoire des messages d'une BAL déléguée, banc de délégation)
**Epic**: E009
**Single frontend**: true
**Priorité**: **2** — les labos qui n'envoient pas encore de CR-BIO en CDA (ou un CDA invalide) arrivent aujourd'hui dans la nouvelle messagerie comme un mail portant un fichier technique illisible : le résultat n'existe ni dans la biologie du patient ni dans les alertes.

> **Origine.** Demande de l'humain du 2026-10-23 : le parsing HPRIM existe dans Weda (WMickey) mais pas dans api-mail. Arbitrages rendus le même jour en séance `/po` (voir « Décisions actées »).
>
> **Suite de l'EPIC** : task-390 (résultats structurés `RES|`), task-391 (file « à intégrer » + suggestion de patient), task-392 (affichage + acquittement + E2E-BIO-003).

## Ce qui est établi

- **api-mail ne lit que l'archive IHE-XDM.** `EnrichmentFetchPlan.IheXdmFileName = "ihe_xdm.zip"` est « la seule pièce jointe utile à l'analyse » ; `IheXdmProcessingService.ExtractIheXdmZipsAsync` (les deux surcharges : IMAP et message en main) ne retient que ce nom. Un `.hpm` n'est ni récupéré ni lu.
- **Modèle d'accueil existant.** `MailMedicalDocument` (patient, traits, `Format`, `Category`, `Body`/`HtmlBody`, PDF associé `HasExternalPdf`/`PdfAttachmentGuid`, doublon `DuplicateOfId` task-013) et `MailMedicalDocumentBiology` (valeur, unité, normes, interprétation, `IsFlagged`).
- **Règle task-176** (`MailRepository.cs`) : un document **sans INS** n'est jamais rattaché automatiquement à un patient ; il va dans la file « à intégrer » (`PatientId == null`). Le HPRIM ne porte pas d'INS.
- **Règle task-193** (`MailRepository.DetectDuplicateAsync`) : **aucune détection de doublon ni de remplacement de version pour un document sans INS** — les requêtes du dossier patient écartent doublons et versions remplacées, et « un document masqué est un risque clinique ». Un HPRIM n'ayant jamais d'INS, il n'est rapproché de rien à la réception (décision 6).
- **Circuit d'écriture existant** : `EmailBuildingService.BuildMailDtoAsync` réunit les `MailMedicalDocumentDto` produits par l'analyse (aujourd'hui `IheXdmProcessingService.ProcessIheXdmZips` → `CdaParsingService`), puis `MailRepository` les persiste (`CreateMedicalDocumentEntity`, `DetectDuplicateAsync`, `AddBiologyResultsToDocument`). Le document HPRIM emprunte **ce même circuit** : pas de nouvelle table, pas de nouveau chemin d'écriture.
- **Référence fonctionnelle Weda** (dépôt `D:\Workspaces\WD`, lecture seule — on copie les règles, on ne dépend pas du code) :
  - `WedaGlobal/Services/Hprim/HprimService.Main.cs` › `PrepareText` : au moins 13 lignes ; en-tête de 12 lignes à positions fixes (`HprimFields` : labo, nom, prénom, adresse 1, adresse 2, ville, date de naissance, NIS, n° de dossier, date du résultat, expéditeur, destinataire) ; corps jusqu'à `****FIN****` ; plusieurs résultats (100 au plus) jusqu'à `****FINFICHIER****` ; rejet d'un contenu commençant par `<!doctype`/`<html` ; données parasites entre `****FIN****` et `****FINFICHIER****` → résultats déjà lus conservés (`HprimInvalidTrailingResultException`).
  - `HprimService.Static.cs` › `IsHprim` (une ligne contient `***FIN***` ou `****FINFICHIER****`), `GetLines` (découpe `\n`, sinon `\r`), `GetEncoding` (BOM UTF-16 BE/LE, UTF-8 ; sinon comptage des `é` puis `è` en 1252 / Mac 10000 / 850 ; défaut ASCII).
  - `WMickey/WMickey.Infrastructure/Mail/MailKitExtensions.cs` › `GetAllAttachments` : le `.hpm` arrive souvent **intégré au corps, sans `Content-Disposition: attachment`** — il faut le récupérer par son nom.
  - Weda PR 9267 (#19121, branches lotus, pas encore dans `next`) : détection sur l'extension `.hpm` seule ; le texte HPRIM ne doit jamais servir de corps du mail.
  - Jeux de cas réels à anonymiser : `Tests/WedaTests/Hprim/` (`GetLinesTests`, `GetEncodingTests`, `PrepareTextTests`, `HprimCommon`), `Tests/Mickey.Application.Tests/Parser/IheXdmParser.cs/HprimParserTests.cs`.

## Décisions actées (humain, 2026-10-23)

1. **Finalité : vue de la nouvelle messagerie uniquement.** L'injection HPRIM dans le dossier Weda reste à WMickey ; E019 inchangé (l'import à la demande continue d'exclure les messages HPRIM).
2. **Identité : file « à intégrer » + suggestion.** Jamais de rattachement automatique (task-176) ; la suggestion de patient par traits est livrée par task-391. Cette US conserve les traits de l'en-tête.
3. **Profondeur : texte + lignes `RES|`.** Cette US crée le document (texte) ; les résultats structurés sont livrés par task-390.
4. **CDA prioritaire, HPRIM en secours.** Le HPRIM n'est lu que si le mail ne porte pas de CR de biologie CDA valide.
5. **Reconnaissance : pièce `.hpm` + marqueurs de fin.** Ni l'objet (`HNET.1/MSG/`) ni le type MIME ne sont regardés.
6. **Doublons : rien n'est rapproché ni masqué à la réception** (règle task-193, arbitrage du 2026-10-23). Le rapprochement — signal doublon existant (task-013) pour un même fichier, remplacement d'un partiel par le complété — se fait **au rattachement**, contre les HPRIM du dossier choisi par le médecin : livré par task-391.
7. **Historique : nouveaux messages seulement.** Pas de rattrapage des messages déjà synchronisés.
8. **BAL déléguée : affichage seul, aucune injection en base** (humain, 2026-10-25, délégation de
   BAL Mailiz — voir task-397 et `Docs/audits/delegation-bal-mailiz-analyse-20261025.md`). Un HPRIM
   porté par un message d'une BAL déléguée (dossier sous `shared/…`) est **lu pour être affiché**,
   en mémoire, à l'ouverture du message.
   - **Rien n'est stocké** chez le délégataire, ni en base ni dans Redis : aucun document, aucun
     trait patient, aucune entrée dans la file « à intégrer ».
   - Hors ligne, il n'est pas consultable.
   - Même règle que pour le CDA délégué (task-397).

## Objective

Quand un mail porte un fichier HPRIM, api-mail en tire un **document médical de biologie** par résultat, en attente de rattachement, au lieu d'un mail avec un fichier technique illisible.

**US backend-only (justification)** : la création du document et sa présence dans la file « à intégrer » sont lues par le test d'intégration ; ce que le médecin voit (suggestion, affichage, acquittement) est livré par task-391 et task-392, qui portent le scénario e2e.

### Règles métier

- **Reconnaissance** : une pièce dont le nom finit par `.hpm` (casse ignorée), **y compris intégrée au corps sans en-tête de pièce jointe**, dont le contenu porte les marqueurs de fin. Un `.hpm` sans marqueurs reste une simple pièce jointe, sans document.
- **Lecture** : règles de Weda ci-dessus (en-tête 12 lignes, plusieurs résultats, encodage détecté, données parasites tolérées, HTML rejeté, fichier trop court rejeté). **Un document par résultat.**
- **Document créé** : catégorie biologie, format HPRIM, date = date du résultat, émetteur = labo/expéditeur, traits patient de l'en-tête (nom, prénom, date de naissance), **sans INS**, **non rattaché**.
- **PDF** : un PDF joint au même mail est associé au document (comme le PDF externe d'un CDA). Plusieurs résultats et un seul PDF : le PDF est associé à chacun.
- **CDA prioritaire** : un mail portant un CR de biologie CDA valide ne produit aucun document HPRIM ; si le CDA est absent ou illisible, le HPRIM est lu.
- **Doublon** : à la réception, **aucun** rapprochement — un HPRIM reçu deux fois donne deux documents à intégrer, aucun n'est masqué (task-193). Le rapprochement se fait au rattachement (task-391).
- **Circuit** : le document HPRIM est produit sous la même forme que le document issu d'un CDA et persisté par le même circuit (voir « Ce qui est établi »).
- **Corps du mail** : le texte HPRIM n'est jamais retenu comme corps.
- **Échec de lecture** : le mail reste un mail normal avec sa pièce jointe ; aucun document partiel, sauf le cas des données parasites (résultats déjà lus conservés).
- **Seuls les messages synchronisés après la mise en service** sont traités.
- **BAL déléguée** (décision 8) : pour un message sous `shared/…`, le HPRIM est lu à l'affichage du
  détail, et ses documents sont renvoyés dans la réponse (texte, PDF associé, traits de l'en-tête
  affichés). **Aucun** n'est persisté ni ajouté à la file « à intégrer ».
  - Le lecteur HPRIM est branché sur le **chemin de lecture en mémoire** des messages délégués
    livré par task-397, pas seulement sur le circuit d'écriture.
  - Le test de convention de task-397 (« aucune écriture issue d'une pièce médicale pour un message
    délégué ») couvre le HPRIM.

## Gherkin

Voir `tests/Features/Mss/HprimReception.feature`.

## Definition of Done

- [ ] Build et tests verts : api-mail
- [ ] ≥ 1 test unitaire par règle de lecture : marqueurs présents/absents, fichier trop court, plusieurs résultats, encodages (UTF-8 BOM, UTF-16 BE/LE, 1252, 850, Mac 10000), données parasites après `****FIN****`, contenu HTML, découpe `\r` seule
- [ ] ≥ 1 test unitaire de reconnaissance : `.hpm` en pièce jointe, `.hpm` intégré au corps sans `Content-Disposition`, `.txt` en `text/plain` non retenu, extension en majuscules
- [ ] Jeu d'exemples HPRIM **anonymisés** (aucun trait réel) dérivé des cas de Weda, versionné avec les tests
- [ ] Test d'intégration de bout en bout (règle 1b) : un mail portant un `.hpm` + PDF, synchronisé, donne un document de biologie au format HPRIM, non rattaché, avec PDF associé, **lu dans la réponse réelle** de la liste des documents à intégrer (cas nominal) ; un `.hpm` sans marqueurs ne donne aucun document (cas d'échec) ; vu rouge
- [ ] Test d'intégration : un mail CDA de biologie valide + HPRIM donne **un seul** document, celui du CDA ; un CDA illisible + HPRIM donne le document HPRIM
- [ ] Test d'intégration : le même HPRIM reçu deux fois → deux documents à intégrer, aucun signalé doublon ni masqué (task-193)
- [ ] Le document HPRIM est persisté par le circuit existant (`MailRepository`), sans nouvelle table ni écriture parallèle
- [ ] Test : le corps d'un mail ne portant qu'un HPRIM n'est pas le texte HPRIM
- [ ] La récupération du message va chercher le `.hpm` en plus de `ihe_xdm.zip` ; aucune régression mesurée sur le banc de charge (E015) pour les mails sans HPRIM
- [ ] Métrique : HPRIM lus, rejetés (par cause), signalés doublons
- [ ] Aucune donnée de santé en clair dans les logs : ni nom, ni prénom, ni date de naissance, ni NIS, ni n° de dossier, ni contenu HPRIM
- [ ] Mails déjà synchronisés avant la mise en service non retraités
- [ ] **BAL déléguée — test d'intégration de bout en bout** (banc de délégation de task-397) : un
      mail portant un `.hpm` + PDF dans `shared/<A>`, ouvert par le délégataire B.
      - Le détail renvoie le document HPRIM décodé, lu dans la réponse réelle.
      - La base de B contient **zéro** ligne `MailMedicalDocuments` pour ce message.
      - Le document est absent de la liste « à intégrer » de B.
      - Aucune clé Redis de B ne contient le texte HPRIM.
      - Vu rouge (règle 1b).
- [ ] Le test de convention de task-397 inclut le chemin HPRIM, prouvé rouge par mutation

## Manual Test Plan

1. Banc de charge / boîte de test : envoyer un mail avec un `.hpm` intégré au corps et un PDF → un document de biologie apparaît dans la file « à intégrer », avec son PDF ; le corps du mail n'affiche pas le texte HPRIM.
2. Renvoyer le même mail → deux documents à intégrer, aucun bandeau doublon (le rapprochement se fait au rattachement, task-391).
3. Envoyer un HPRIM contenant deux résultats → deux documents.
4. Envoyer un mail CDA de biologie valide + HPRIM → un seul document, issu du CDA.
5. Envoyer un `.hpm` sans marqueurs de fin → mail normal, pièce jointe intacte, aucun document.
6. Vérifier dans Seq qu'aucun trait patient ni contenu HPRIM n'apparaît.
7. **BAL déléguée.** Envoyer un HPRIM à Virginie, puis se connecter en Cyril, son délégataire, et
   ouvrir le message dans la boîte déléguée.
   - Le résultat est **lisible**.
   - Aucun document n'apparaît dans la file « à intégrer » de Cyril, et sa base ne contient aucun
     document pour ce message.
   - Hors ligne, le message s'affiche avec sa pièce jointe seule.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : biologie médicale (réception en médecine de ville)
- **Vague Ségur** : hors Ségur — le HPRIM est un format historique hors CI-SIS ; le CR-BIO CDA exigé par le Ségur reste prioritaire (décision 4)
- **Exigences DSR honorées** : identito-vigilance — aucun rattachement d'un document sans INS ; le document structuré CI-SIS prime sur le format historique
- **INS** : non disponible dans le format ; traits de l'en-tête conservés pour une suggestion (task-391), jamais pour un rattachement automatique (task-176)
- **Authentification PS** : inchangée — traitement serveur à la synchronisation de la boîte
- **Habilitations** : documents de la boîte du médecin. Pour une BAL déléguée, lecture seule
  sans stockage chez le délégataire (décision 8, task-397).
- **Interop CI-SIS** : non applicable — HPRIM Santé (format historique propriétaire, texte libre + lignes `RES|`)
- **Tracé PGSSI-S** : aucun nouvel évènement d'imputabilité (création automatique à la réception, comme un CDA) ; journal technique sans donnée identifiante
- **Consentement patient** : non applicable — aucun envoi vers le DMP ni Mon Espace Santé
- **Référentiels métier** : aucun dans cette US (codes labo locaux traités en task-390)
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé — même traitement (réception de résultats de biologie), nouveau format d'entrée
