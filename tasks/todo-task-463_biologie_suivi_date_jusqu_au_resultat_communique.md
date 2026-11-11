# todo-task-463.md — Biologie : suivi daté jusqu'au résultat communiqué

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Dependencies**: done-task-453 (acquittements durables), done-task-454 (« traité » et acquittement)
**Epic**: E024
**Priorité**: EPIC E024, demandée par l'humain le 2026-11-11. Douleur n° 2 (biologie : 4/5). L'acquittement
enregistre la décision, mais rien ne garantit qu'elle est **suivie** : l'appel au patient, la convocation, le contrôle.

> **Origine.** Analyse du 2026-11-11, manque A4. Modèle australien : Best Practice Omni (« No action / Non urgent
> appointment / Urgent appointment », file de suivi jusqu'à « Mark result as given »), HotDoc, Zedmed.

## Ce qui est établi

- `BiologyAck`, en ajout seul :
  - actions `Acknowledged`, `PatientCalled`, `PatientSummoned`, `ReferredToColleague`, `MarkResolved` ;
  - note de 500 caractères ;
  - état dérivé de la dernière action (`Pending`, `InProgress`, `Resolved`) ;
  - **aucune échéance**.
- Service `BiologyAckService` (`RecordAckAsync`, rejeu hors ligne), contrôleur `BiologyAcksController`
  (`POST api/v1/medical-documents/{documentId}/biology-ack`, `pending-mail-uids`, `pending-summary`).
- Les enums sont dans le paquet DTO (`BiologyAckActionType`, `BiologyAckResolutionState`). Toute valeur ajoutée va
  **en fin** d'enum.
- task-454 : « Traité » ajoute `MarkResolved` ; un message dont tous les documents sont résolus est traité.
- Garde-fou de task-392 : seule l'anomalie posée par le laboratoire est une anomalie.

## Objective

Après la lecture d'un résultat, le praticien **décide** : « Rien à faire », « Revoir le patient » ou « Revoir le patient
en urgence ». Les deux dernières décisions ouvrent un **suivi daté**, qui reste visible jusqu'à **« Résultat communiqué
au patient »**. Un suivi en retard revient dans « À traiter ».

Règles :
- **Trois décisions** proposées en tête du panneau d'acquittement :
  1. **Rien à faire** : enregistre `MarkResolved` avec la note « Rien à faire » ; le message est traité (task-454).
  2. **Revoir le patient** : échéance proposée à J+7, modifiable.
  3. **Revoir le patient en urgence** : échéance proposée à J+1, modifiable, et le suivi est signalé comme urgent.

  Les cinq actions existantes restent disponibles en dessous.
- **Un suivi est ouvert** tant qu'aucune de ces actions n'est enregistrée : **Résultat communiqué au patient**
  (nouvelle action), Patient convoqué, Adressé à un confrère, Résolu. Rappeler le patient sans le joindre laisse le
  suivi ouvert.
- **Vue « Suivis biologie »** :
  - la liste des suivis ouverts, triés par échéance : patient, examen, décision, échéance, auteur ;
  - filtres « En retard », « Aujourd'hui », « Cette semaine » ;
  - une tuile de tableau de bord derrière le flag `dashboard_widget_biology_followups`.
- **En retard** : un suivi dont l'échéance est passée fait revenir son message dans « À traiter » (task-454), avec le
  bandeau « Suivi en retard depuis le … — décidé par {Prénom NOM} ».
- **Chaque décision et chaque clôture est imputée** (règle 14), et l'historique d'acquittement les montre dans l'ordre.
- **Le système ne décide jamais** : aucune décision proposée par défaut à partir des valeurs. L'anomalie reste celle
  du laboratoire.

### Hors périmètre

- Envoyer au patient un message « résultat normal » par Mon espace santé : à rédiger après task-464.
- Prise de rendez-vous.

## Definition of Done

- [ ] Enum `BiologyAckActionType` étendue **en fin** (décisions « revoir », « revoir en urgence », « résultat
      communiqué ») ; échéance nullable sur l'acquittement, compatible avec l'ajout seul (migration FluentMigrator,
      audit règle 7c) ; paquet DTO publié ; miroirs TypeScript.
- [ ] Actes d'audit pour chaque nouvelle action, au nom de la personne ; `HealthDataAccess`.
- [ ] Tests unitaires : suivi ouvert et fermé par chaque action de clôture ; « patient rappelé » le laisse ouvert ;
      retard calculé dans le fuseau Europe/Paris ; « Rien à faire » traite le message.
- [ ] **Test d'intégration de bout en bout (règle 1b)** sur `POST api/v1/medical-documents/{id}/biology-ack` puis la
      vue des suivis :
      - « Revoir en urgence » à J+1, horloge avancée de 2 jours : le suivi est lu « en retard » et le message revient
        dans « À traiter » ;
      - « Résultat communiqué » le ferme ;
      - cas d'échec : une échéance dans le passé à la décision → 400 en `ProblemDetails`.
      Vu rouge.
- [ ] **Deux personnes sur la même boîte** : le titulaire décide, la secrétaire déléguée enregistre « Résultat
      communiqué » ; l'historique montre les deux auteurs réels.
- [ ] Tests de composant (weda2 et mobile), vus rouges par mutation : trois décisions, échéance modifiable, vue
      « Suivis biologie », filtres, bandeau « Suivi en retard », tuile.
- [ ] **Scénarios e2e**, mobile et angular requis, vus rouges :
      - `E2E-BIO-005` v1 : décider « Revoir le patient » sur le compte rendu à acquitter crée un suivi daté visible
        dans « Suivis biologie » ;
      - `E2E-BIO-006` v1 : « Résultat communiqué au patient » ferme le suivi.
- [ ] `data-testid`, conventions de libellés, aucune donnée de santé dans les logs.
- [ ] Build et tests verts (api-mail, Dtos, weda2, mobile) ; client-angular : code-only.

## Manual Test Plan

1. Backend et weda2 sur la boîte de formation (comptes rendus de biologie HPRIM et CDA).
2. Ouvrir un compte rendu anormal, choisir « Revoir le patient en urgence » : l'échéance proposée est demain.
3. Ouvrir « Suivis biologie » : le suivi y est, avec le patient, l'examen, l'échéance et votre nom.
4. Changer l'échéance à hier (ou avancer l'horloge du poste de test) : le message revient dans « À traiter », avec
   « Suivi en retard ».
5. Mobile, secrétaire déléguée : enregistrer « Résultat communiqué au patient ». Le suivi disparaît ; l'historique
   montre vos deux noms.
6. Sur un résultat normal : « Rien à faire ». Le message est traité.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville / biologie médicale (réception des comptes rendus)
- **Vague Ségur** : V2 — exploitation des comptes rendus de biologie structurés
- **Exigences DSR honorées** : prolonge LGC.MDV.08 et 09 (comptes rendus de biologie intégrés et suivis) ; à confirmer
  dans le DSR du couloir médecin de ville
- **INS** : inchangé — le suivi porte sur un document déjà rattaché ; aucune INS n'est affichée dans la vue
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel
- **Habilitations** : personnes de la boîte sous verdict de l'opérateur (règle 14) ; la décision clinique reste au
  praticien ; la secrétaire peut enregistrer « Résultat communiqué »
- **Interop CI-SIS** : CR de biologie CDA R2 N3 et HPRIM, lecture inchangée
- **Tracé PGSSI-S** : chaque décision et clôture au nom de la personne ; retour d'un suivi en retard en acte système ;
  `HealthDataAccess`, 3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : LOINC et codes de laboratoire, inchangés
- **Hébergement HDS** : oui — base de la boîte
- **AIPD / impact RGPD** : à mettre à jour — nouvelle donnée de suivi clinique (décision et échéance) liée à un patient
