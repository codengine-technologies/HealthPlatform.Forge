# todo-task-467.md — Biologie : l'anomalie du laboratoire n'est jamais perdue

**Repos**: api-mail, client-angular, client-mobile
**Dependencies**: aucune
**Epic**: E025
**EpicTitle**: Audit 2026-11 : sécurité et fiabilité
**Priorité**: EPIC E025, issue de l'audit de sécurité et de bugs du 2026-11-12/13, validée par l'humain le
2026-11-13. **Première du lot** : c'est le risque patient le plus direct. Elle touche le dépôt d'acquittements
(`BiologyAckRepository`) comme task-466 : si task-466 passe d'abord, partir de son `develop`.

> **Origine.** Audit en lecture seule du 2026-11-12/13 (agents « données, audit, IA », « bugs Angular », « bugs
> mobile »). Trois audits indépendants ont relevé le même trou : un code de laboratoire hors de la liste fermée du
> serveur n'est signalé nulle part. Constats relus dans le code par l'orchestrateur le 2026-11-13.

## Ce qui est établi

Lecture du code au 2026-11-13 :

- **Liste fermée, sensible à la casse.** `Application/Helpers/BiologyInterpretation.cs:10-14` ne reconnaît que
  `L`, `A`, `H`, `LL`, `AA`, `HH`, comparés tels quels. Un code HL7 `<` ou `>` (hors échelle de mesure), `LU`, `HU`,
  ou un `h` / `H ` venu d'un CDA (`CdaParsingService`, code brut ni rogné ni mis en majuscules) rend
  `IsFlagged = false` : ni widget des anormaux, ni « à acquitter », ni `HasAbnormalBiology`.
- **Deux règles divergentes.** L'assistant IA juge « anormal » tout code non vide différent de `N`
  (`AiConversationService.cs:511-512` et `:527`) : il dit « anormal » pour un résultat que l'écran montre normal.
- **Web : le vert passe avant le signalement.** `libs/mss/src/ui/biology-value/biology-value.component.ts:102` rend
  `normal` dès que la valeur est dans les bornes, avant de lire `isFlagged`. Le parseur (`:144`) retire `<` et `>` et
  colle tous les chiffres : « < 0,10 » avec bornes 0,10–0,50 et code `L` s'affiche en vert.
- **Frises : `A` et `AA` non marqués.** `getInterpretationClass` traite `N`, `L`, `H`, `LL`, `HH` et rend `''`
  sinon, sur mobile (`features/patient/components/biology-timeline/biology-timeline.component.ts:276`) comme sur web
  (`libs/mss/src/features/patient/components/biology-timeline/biology-timeline.component.ts:358`). Une sérologie
  positive codée `A` paraît neutre.
- **Mobile : norme à une borne masquée.** `features/mail/components/biology/biology.component.ts:142` n'affiche la
  norme que si les deux bornes existent (`if (min && max)`).
- **Biologie d'une fiche : documents inactifs inclus.** `Infrastructure/Repositories/MailDb/BiologyRepository.cs:57`
  ne filtre que `PatientId`. Le prédicat « document actif » de la frise (`PatientRepository.ActiveDocumentsForPatient`,
  `:642-658` : retrait accepté, version remplacée, doublon, dossiers Envoyés / Brouillons / Corbeille) n'y est pas
  appliqué. `BiologyAckRepository` (`GetPendingSummaryAsync`, `GetPendingMailUidsAsync`,
  `GetPendingMailUidsByActionAsync`) n'en applique aucun non plus : ses compteurs divergent du widget.
- **Widget « anormaux non lus ».** `BiologyRepository.cs:189-240` groupe par message seul, prend l'identité du
  **premier** document (un mail HPRIM à deux patients montre les valeurs des deux sous un seul nom), et applique
  `Take(maxPatients)` **avant** le tri « critique d'abord » : un `HH` peut manquer quand des `H` sont présents.
- **Pannes muettes.** Web : `ui/abnormal-biology-widget/abnormal-biology-widget.component.ts:67-69` éteint le
  chargement sur erreur et le gabarit affiche « Aucun résultat anormal non lu ». Mobile :
  `biology-ack-pending-tile.component.ts:111` pose un résumé vide (« Aucune biologie en attente d'acquittement ») ;
  `inbox-biology-ack-chip.component.ts:119` applique un ensemble vide et vide la liste.
- **Acquittement.** Web : `mail-detail.component.ts:2057` ignore `ackFailed`, le panneau n'a pas de zone d'erreur.
  Mobile : `biology-ack-panel.component.ts:208-216` bascule l'état avant la réponse et lie la requête à la vie de la
  page (`takeUntilDestroyed`) : quitter l'écran annule l'acte sans retour arrière. Serveur :
  `BiologyAckService.cs:185-215` écrit la ligne puis lève sur une action hors énumération (400 sans trace, ligne
  orpheline).

## Objective

Un résultat que le laboratoire a signalé anormal est **toujours** vu par le médecin, sur le serveur, le web et le
mobile ; une valeur corrigée ou retirée par le laboratoire ne reste pas affichée ; une panne ne se fait jamais passer
pour « rien à signaler ».

Règles :

1. **Une seule règle « signalé par le laboratoire »**, portée par `BiologyInterpretation`, partagée par le CDA, le
   HPRIM, l'assistant IA et rendue aux clients par `IsFlagged` (les clients ne recalculent pas).
   - Codes d'anomalie HL7 (table 0078) : `L`, `H`, `LL`, `HH`, `LU`, `HU`, `A`, `AA`, `<`, `>`. Comparaison après
     retrait des espaces et mise en majuscules.
   - Critiques : `LL`, `HH`, `AA` (inchangé).
   - **Un code inconnu n'est pas signalé** (décision humaine du 2026-11-13). Il est compté dans une métrique (code
     seul, aucune donnée de santé) pour qu'un code nouveau d'un émetteur se voie.
   - Rappel (task-392) : seule l'indication du laboratoire fait une anomalie ; les bornes ne sont qu'un affichage.
2. **L'affichage suit le signalement.**
   - Une valeur signalée n'est jamais affichée « normale », même comprise dans les bornes.
   - Une valeur à comparateur (`< 0,10`, `> 500`) est non numérique : affichée telle quelle, sans position sur la
     jauge.
   - Les deux frises marquent toute valeur signalée (`A`, `AA` compris), critique pour `LL`, `HH`, `AA`.
   - Mobile : une norme à une seule borne s'affiche (« < 5 »).
   - Une valeur hors bornes non signalée reste neutre (inchangé).
3. **Documents actifs seulement** : la biologie d'une fiche patient (`GET biology/patients/{id}`), les compteurs et la
   file « à acquitter » appliquent le **même** prédicat que la frise des documents, écrit une seule fois.
4. **Widget « anormaux non lus »** : une entrée par couple (message, patient), sous l'identité de ce patient ; tri
   critique d'abord puis date, **avant** la coupe.
5. **Une panne n'est pas « rien »** : widget des anormaux (web), tuile et puce « Bio à acquitter » (mobile) affichent
   « Indisponible » avec « Réessayer ». La puce ne s'active pas sur un ensemble qu'elle n'a pas pu lire.
6. **Acquittement** :
   - web : un échec s'affiche dans le panneau (message tiré du `ProblemDetails`), avec « Réessayer », et la note
     saisie est conservée ;
   - mobile : l'écriture ne dépend plus de la vie de l'écran ; un échec rétablit l'état et s'affiche ;
   - serveur : une action hors énumération est refusée en 400 **avant** toute écriture.

### Hors périmètre

- La date de début du suivi (task-466) et le suivi daté jusqu'au résultat communiqué (task-463).
- Le PDF HPRIM associé à chaque document et les dates HPRIM (task-468).
- Les codes de sensibilité d'un antibiogramme (`S`, `I`, `R`) et les qualitatifs (`POS`, `NEG`) : ils ne sont pas des
  anomalies au sens de la table 0078 et restent non signalés.

## Definition of Done

- [ ] `BiologyInterpretation` porte la règle unique (codes, normalisation, critiques) ; `CdaParsingService`,
      `HprimStructuredResults` et `AiConversationService` l'appellent, aucune liste locale ne subsiste.
- [ ] Tests unitaires de la règle : chaque code de la liste, minuscules, espaces autour, `N`, `S`, `R`, `POS` non
      signalés, code inconnu non signalé et compté par la métrique.
- [ ] **Test d'intégration de bout en bout (règle 1b)** : un CDA de biologie porteur d'un résultat `>` et d'un
      résultat ` h` est ingéré ; `GET biology/patients/{id}` lit `IsFlagged = true` sur les deux, ils sont comptés par
      `GET biology-acks/pending-summary` et présents dans le widget des anormaux non lus. Cas d'échec : un résultat `N`
      reste `IsFlagged = false`. Vu rouge.
- [ ] **Test d'intégration des documents actifs** : une v2 d'un CR-BIO remplace la v1 ; la v1 est absente de
      `GET biology/patients/{id}`, de `pending-summary` et de `pending-mail-uids`. Un doublon confirmé compte une fois ;
      un document au retrait accepté est absent. Vu rouge.
- [ ] **Test d'intégration du widget** : onze mails non lus porteurs d'anomalies, dont un `HH` le plus ancien ; le
      `HH` est dans la réponse. Un mail portant les documents de deux patients donne deux entrées, chacune sous
      l'identité de son patient. Vu rouge.
- [ ] **Test d'intégration de l'acquittement** : une action hors énumération rend 400 en `ProblemDetails`, sans ligne
      `BiologyAcks` ni trace. Vu rouge.
- [ ] **Deux personnes sur la même boîte** (règle 14) : le délégataire acquitte un résultat ; le titulaire relit
      l'état ; la trace d'audit porte le délégataire (RPPS, nom, rôle).
- [ ] Tests de composant web et mobile, vus rouges par mutation : valeur signalée dans les bornes jamais « normale » ;
      comparateur non placé sur la jauge ; `A` et `AA` marqués dans les deux frises ; norme à une borne (mobile) ;
      états « Indisponible » du widget, de la tuile et de la puce ; échec d'acquittement affiché, note conservée (web) ;
      échec d'acquittement rétabli et affiché (mobile).
- [ ] **Scénario e2e** `E2E-BIO-008` v1 ajouté à `Api/Mail/e2e/scenarios.yml`, mobile et angular requis : « un résultat
      hors échelle signalé par le laboratoire apparaît dans les anormaux et à acquitter ». Le seed du banc porte un
      résultat `>`.
- [ ] Trou du filet : scénario `E2E-BIO-008` prouvé rouge sur le code non corrigé, ligne ajoutée dans
      `conventions/e2e.md`.
- [ ] Prévention (règle d'or) :
      - `conventions/csharp.md` : « l'anomalie d'un résultat se lit par `BiologyInterpretation`, jamais par une liste
        locale ; un compteur de biologie applique le prédicat « document actif » » ;
      - `conventions/angular.md` : « une panne n'est jamais rendue comme un état vide : état « indisponible » et
        « Réessayer » ».
- [ ] Aucune donnée de santé dans les logs (la métrique des codes inconnus ne porte que le code) ; `data-testid` sur
      chaque élément interactif ajouté.
- [ ] Build et tests verts : `HealthPlatform.Api.Mail.sln`, weda2 (`nx build weda2`, `nx test weda2`,
      `nx test mss-lib`), client-mobile (`npm run build`, `npm test -- --watch=false --browsers=ChromeHeadless`).
- [ ] client-angular : code-only, aucun commit.

## Manual Test Plan

1. Lancer le backend (`cd Api/Mail/src/AppHost && dotnet run`), weda2 (`cd Client/Angular/front && npm start`) et le
   mobile (`cd Client/Mobile && npm start`).
2. Injecter dans la boîte de test un CR-BIO CDA avec un potassium codé `>` et une glycémie codée `L` dont la valeur est
   comprise dans les bornes (`Tools/EmlFactory`, `--verify` avant injection).
3. Ouvrir le mail (web, mobile) : les deux valeurs sont marquées anormales, aucune n'est verte. Le potassium « > … »
   n'est pas placé sur la jauge.
4. Tableau de bord : le patient apparaît dans « Résultats anormaux non lus » ; la puce et la tuile « Bio à acquitter »
   le comptent.
5. Fiche patient, onglet biologie et frise : les deux valeurs sont marquées.
6. Injecter une v2 du même compte rendu (valeurs corrigées) : la v1 disparaît de la fiche et des compteurs.
7. Arrêter l'API puis recharger le tableau de bord (web) et l'accueil (mobile) : widget, tuile et puce affichent
   « Indisponible » et « Réessayer », jamais « aucun ».
8. API arrêtée, acquitter un résultat (web) : le panneau affiche l'échec et garde la note.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville / biologie médicale (réception des comptes rendus)
- **Vague Ségur** : V2 — exploitation des comptes rendus de biologie structurés
- **Exigences DSR honorées** : prolonge LGC.MDV.08 et 09 (comptes rendus de biologie intégrés) ; à confirmer dans le
  DSR du couloir médecin de ville
- **INS** : inchangé — le widget sépare les patients d'un même mail sous leur propre identité ; aucune INS n'est
  ajoutée à l'affichage
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel
- **Habilitations** : personnes de la boîte sous verdict de l'opérateur (règle 14) ; le signalement reste le jugement
  du biologiste
- **Interop CI-SIS** : CR de biologie CDA R2 N3 (`interpretationCode`, table HL7 0078) et HPRIM (champ 8 de `RES|`),
  lecture élargie aux codes `<`, `>`, `LU`, `HU`
- **Tracé PGSSI-S** : acquittement imputé à la personne réelle ; action refusée sans trace d'acte ; `HealthDataAccess`,
  3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : HL7 table 0078 (indicateurs d'anomalie), LOINC inchangé
- **Hébergement HDS** : oui — base de la boîte
- **AIPD / impact RGPD** : inchangée — aucune donnée nouvelle, correction de l'affichage et des compteurs
