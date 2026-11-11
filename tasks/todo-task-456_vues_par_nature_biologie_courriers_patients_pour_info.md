# todo-task-456.md — Vues par nature : biologie, courriers, patients, pour info

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Dependencies**: done-task-454 (état « traité », compteur « à traiter »), done-task-465 (mesure de charge)
**Epic**: E024
**Priorité**: EPIC E024, demandée par l'humain le 2026-11-11. Douleur n° 7 (2/5). Ce sont les messages générés
par des machines qui pèsent le plus sur la charge du médecin (Tai-Seale, Health Affairs 2019).

> **Origine.** `Docs/analyse-fonctionnelle-manques-messagerie-2026-11.md`, manques B1 et B2 (HEY Imbox / Feed / Paper
> Trail, onglets Gmail, Apple Mail, Superhuman Split Inbox). Nom « Pour info » validé par l'humain le 2026-11-11.

## Ce qui est établi

- La nature clinique existe **par document**, pas par message :
  - `MailMedicalDocument.Category` porte le `DocumentType` (Bio, Synth, Imagerie, Consultation, Hospitalisation…,
    14 types) ;
  - `Format` vaut CDA, HPRIM ou EMAIL ;
  - la catégorie est calculée à l'ingestion (`CdaParsingService`, `HprimMedicalDocuments`).
- Un message patient (MES) se reconnaît à l'expéditeur `@patient.mssante.fr`. `MailDto.IsFromPatient` est calculé à
  la volée, sans colonne.
- Un message sans document médical n'a **aucune catégorie**.
- Les vues `tag:XXX` existent (`GetTagFoldersAsync`, route `mail/tag/:tagCode`). Une nature calculée en SQL pour les
  compteurs exige une colonne sur `Mails`.
- `AddCategoryTagsToMailAsync` (Type `"CATEGORY"`) est du code mort, sans appelant.

## Objective

La Boîte de réception se lit **par nature**. Quatre vues, chacune avec son compteur « à traiter », que le praticien
parcourt dans l'ordre qu'il veut. Les messages « pour info » ne se mêlent plus aux comptes rendus.

Règles :
- **Les quatre natures** :
  1. **Biologie** : le message porte au moins un document de biologie (CDA LOINC 11502-2 ou HPRIM).
  2. **Patients** : message d'un patient (Mon espace santé).
  3. **Courriers et comptes rendus** : tout autre message adressé à la boîte (en destinataire principal) par un
     professionnel ou un établissement, avec ou sans document.
  4. **Pour info** : la boîte n'est qu'**en copie** ; message **automatique** (en-têtes `Auto-Submitted`, `List-Id`,
     `Precedence: bulk`) ; avis techniques et rapports de distribution (jusqu'à task-460, qui les range sous le
     message d'origine).
- **Une seule nature par message**, choisie dans l'ordre Biologie > Patients > Courriers et comptes rendus > Pour info.
  Elle est calculée **une fois**, à l'arrivée du message, et stockée.
- **Le praticien peut corriger** : « Changer la nature » sur un message. Le geste est imputé, et l'auteur s'affiche.
- **Où** :
  - weda2 : un groupe « À traiter » en tête de l'arborescence des dossiers, avec les quatre vues et leurs compteurs ;
  - mobile : quatre puces au-dessus de la liste de l'Accueil et de la Boîte de réception. Elles remplacent le
    regroupement local « BIOLOGIE À VALIDER / AUTRES MESSAGES » de `inbox.page`.
- **Traiter d'un coup** :
  - dans chaque vue, « Traiter les N messages affichés » avec confirmation du nombre ;
  - dans **Biologie**, « Traiter les résultats sans anomalie » : n'inclut que les messages dont aucun résultat ne porte
    l'indicateur d'anomalie posé par le laboratoire (garde-fou de task-392 : jamais une comparaison aux bornes) ;
  - chaque message traité de cette façon suit les règles de task-454 (biologie passée « Résolue » et imputée).
- **Pages servies par le serveur**, dans l'ordre de réception le plus récent.
- **Messages existants** : la nature est calculée pour les messages déjà en base à la première ouverture de la boîte
  après la mise à jour, sans action du praticien.

### Hors périmètre

- Les règles de tri automatiques définies par l'utilisateur.
- Les autres dossiers de réception : la v1 couvre la Boîte de réception.
- Le regroupement visuel des notifications d'un même expéditeur sur une ligne.

## Definition of Done

- [ ] Nature stockée par message : migration FluentMigrator, calcul à l'ingestion (`AddNewMailConsumer` et chemin
      d'enrichissement), rattrapage des messages existants ; audit de migration (règle 7c).
- [ ] Contrat : nature dans `MailDto` ; vues et compteurs « à traiter » par nature ; changement de nature ; paquet DTO
      publié.
- [ ] Acte d'audit `MailNatureChanged` (personne) ; le traitement groupé produit un `MailMarkedHandled` par message ;
      miroirs TypeScript.
- [ ] Code mort `AddCategoryTagsToMailAsync` retiré ou réutilisé (justifié dans le `## Develop log`).
- [ ] Mesure de charge (task-465) : indicateur « volume reçu et reste à traiter par nature » ajouté au tableau de bord,
      avec son test unitaire.
- [ ] Tests unitaires de la règle de nature : un test par nature, dont copie seule, `Auto-Submitted`, message de
      patient porteur d'une biologie (→ Biologie), message d'un confrère sans document (→ Courriers).
- [ ] **Test d'intégration de bout en bout (règle 1b)** sur la vue par nature (`GET api/v1/Mail/natures/{nature}/emails`
      ou équivalent) : un jeu de quatre messages, chacun lu dans la bonne vue avec le bon compteur ; « Traiter les
      résultats sans anomalie » traite le résultat normal et **laisse** le résultat anormal. Cas d'échec : nature
      inconnue → 400 en `ProblemDetails`. Vu rouge.
- [ ] **Deux personnes sur la même boîte** : le délégataire change la nature, le titulaire lit la nouvelle nature et
      son auteur.
- [ ] Tests de composant (weda2 et mobile), vus rouges par mutation : vues et compteurs, changer la nature, traiter
      les N messages, traiter les résultats sans anomalie (le message anormal reste).
- [ ] **Scénarios e2e**, mobile et angular requis, vus rouges :
      - `E2E-TRIAGE-005` v1 : le compte rendu de biologie est dans « Biologie », le message du patient dans
        « Patients », une copie dans « Pour info », chacun avec son compteur ;
      - `E2E-TRIAGE-006` v1 : « Traiter les résultats sans anomalie » laisse le résultat anormal à traiter.
- [ ] `data-testid`, conventions de libellés, aucune donnée de santé dans les libellés ni les logs.
- [ ] Build et tests verts (api-mail, Dtos, weda2, mobile) ; client-angular : code-only.

## Manual Test Plan

1. Backend et weda2 lancés sur la boîte de formation de Virginie (corpus réel : comptes rendus, biologie, copies).
2. Le groupe « À traiter » montre Biologie, Patients, Courriers et comptes rendus, Pour info, avec leurs compteurs.
   Leur somme égale le compteur « À traiter » de la Boîte de réception.
3. Ouvrir « Pour info » : seuls des messages où la boîte est en copie ou des messages automatiques.
4. Sur un message de « Pour info », « Changer la nature » vers « Courriers et comptes rendus » : il change de vue ; le
   détail dit qui l'a reclassé.
5. Dans « Biologie », « Traiter les résultats sans anomalie » : seuls les résultats sans indicateur d'anomalie du labo
   sortent ; les anormaux restent.
6. Mobile : les quatre puces au-dessus de la liste, mêmes compteurs que weda2.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — organisation du travail
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel
- **Habilitations** : titulaire, membre, délégataire, sous verdict de l'opérateur (règle 14)
- **Interop CI-SIS** : lecture des catégories de documents CDA R2 (LOINC du type de document) et HPRIM, inchangée
- **Tracé PGSSI-S** : `MailNatureChanged` et `MailMarkedHandled` au nom de la personne ; calcul de la nature et
  rattrapage en acte système ; `HealthDataAccess`, 3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : LOINC (types de documents)
- **Hébergement HDS** : oui — base de la boîte
- **AIPD / impact RGPD** : inchangé — aucune donnée nouvelle sur le patient
