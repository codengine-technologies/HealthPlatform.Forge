# todo-task-413 — Traçabilité de tous les actes sur la boîte partagée

**Repos**: api-mail, client-angular
**Dependencies**: task-407 (`SmtpService` et les traces d'envoi modifiés)
**Epic**: E020

> **Origine** : audit du périmètre « boîte déléguée » du 2026-10-30
> (`Docs/audits/2026-10-30-audit-boite-deleguee.md`). Constats M5, M6, M7, m8 à m12 et m14.
> `client-angular` : seulement le scénario du journal (E2E-AUDIT-001), que mobile n'a pas.

## Objectif

Chaque acte sur une boîte est tracé au nom de la personne réelle, dans le journal de la boîte
concernée, avec son objet (règle 14). C'est vrai aussi pour une lecture faite après un autre
lecteur. Un acte fait par le système est tracé comme acte système. Le test d'architecture rend
impossible une action déclarée tracée qui ne trace rien.

## Règles

1. **La lecture d'un message est tracée pour chaque personne** (M5). Ouvrir le contenu ou le résumé
   d'un message trace `MailRead` au nom de la personne, que le message soit déjà lu ou non. Une
   lecture répétée dans une courte fenêtre ne crée pas de doublon : une seule trace par personne,
   par message et par fenêtre, fenêtre à fixer par `/develop` et justifiée. Les exemptions « tracée
   au passage à lu » sont retirées.
2. **Le journal de la boîte visée** (M6). Chaque trace de gestion porte la boîte visée, pas la boîte
   ouverte :
   - `MailboxId`, `MailboxAddress` et `ActorRole` (le rôle sur la boîte visée, ou aucun s'il n'y en
     a pas encore) ;
   - cela vaut pour le rattachement, le détachement, la réauthentification, la boîte par défaut et
     les refus.

   `Impute` ne complète plus ces champs quand la trace a déjà une boîte (`TenantId`). Un refus sans
   boîte connue reste lisible par l'exploitation et est documenté.
3. **Les marquages tracent vraiment** (M7). Les actions marquées `[TracedInCode]` émettent la trace
   annoncée :
   - non-lu, marquages en masse, signalé et non signalé ;
   - leur rejeu hors ligne.

   Le test d'architecture vérifie que **la méthode atteinte** par l'action trace, et plus seulement
   que la chaîne `AuditActionType.X` existe quelque part dans le code.
4. **Traces de refus complètes** (m8). Une trace de refus ou de suspension d'accès porte le nom, le
   RPPS et le rôle de la personne, même quand le verrou passe avant l'enrichissement du contexte, et
   même hors ligne. Les traces du préremplissage portent le RPPS.
5. **Actes système** (m9, m10) :
   - les consommateurs du bus qui écrivent des étiquettes ou des contacts tracent un acte système ;
   - la réception d'un message et le traitement d'un CDA par la synchro de fond sont des **actes
     système** (`IsSystemAct`, aucun acteur), et non des actes de la personne qui a lancé la synchro.
6. **L'objet d'une consultation patient** (m11). `POST /patients/resolve` et `POST /patients/mails`
   tracent l'identifiant du patient consulté (identifiant technique, jamais l'INS en clair).
7. **INS hors des journaux techniques** (m12). Les adresses `{INS}@patient.mssante.fr` sont masquées
   dans les logs d'envoi (`SmtpService`) et partout où une adresse de destinataire est journalisée.
   Le masquage est centralisé, pas dupliqué par appel.
8. **Rattachement refusé par la sonde** (m14). Il est tracé comme les autres refus, et l'adresse
   vide aussi.
9. **Journal** : tous les champs restent visibles des co-utilisateurs, y compris l'IP, le navigateur
   et l'identifiant technique (décision humaine du 2026-10-30). Rien à changer.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures)
- [ ] Unit tests :
  - `Impute` ne remplace pas la boîte d'une trace qui en porte une ;
  - lecture tracée avec fenêtre de dédoublonnage ;
  - acte système de la synchro et des consommateurs ;
  - masquage des adresses patient.
- [ ] Test d'architecture durci, vu rouge sur l'un des marquages non tracés d'aujourd'hui
- [ ] Test d'intégration de bout en bout, **deux personnes sur la même boîte** : le titulaire lit un
      message, puis le délégataire le lit. Le journal (`GET /api/v1/audit/traces`) porte **deux**
      `MailRead`, l'un au nom du titulaire et l'autre au nom du délégataire (RPPS, rôle). Vu rouge
      (règle 1b).
- [ ] Test d'intégration de bout en bout : boîte A ouverte, la personne détache la boîte B. La trace
      est dans le journal de B, pas dans celui de A. Vu rouge.
- [ ] Test d'intégration de bout en bout pour chaque marquage (non-lu, lu en masse, signalé, non
      signalé) : la trace porte la personne et le message. Vu rouge.
- [ ] Test d'intégration de bout en bout : un refus d'accès hors ligne porte RPPS, nom et rôle. Vu
      rouge.
- [ ] Test d'intégration de bout en bout : un message reçu pendant la synchro d'un délégataire est
      tracé comme acte système. Vu rouge.
- [ ] Test d'intégration de bout en bout pour `POST /patients/resolve` : la trace porte
      l'identifiant du patient. Vu rouge.
- [ ] Test d'intégration de bout en bout : un rattachement refusé par la sonde laisse une trace de
      refus. Vu rouge.
- [ ] Logs d'un envoi à un patient : aucune occurrence de l'INS (test sur la sortie du logger)
- [ ] Scénario **E2E-AUDIT-001 v2** (angular requis, mobile non applicable : pas d'écran de journal
      sur mobile). Le titulaire lit au journal que le délégataire **a lu** un message, en plus de la
      suppression de la v1. Implémenté dans weda2.
- [ ] Évènements PGSSI-S journalisés : `MailRead` par personne, marquages, refus complets, actes
      système. Conservation 3 653 jours (`HealthDataAccess`).

## Manual Test Plan

- Backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil e2e). weda2 via le faux hôte.
- Le titulaire lit un message, puis le délégataire le lit. Dans weda2, le journal de la boîte
  affiche deux lectures, chacune au nom de son auteur.
- Le délégataire retire le signalement d'un message. Attendu : la trace à son nom.
- Boîte A ouverte, détacher la boîte B. Attendu : la trace est dans le journal de B.
- Dans Seq, après un envoi à une adresse patient : aucune adresse `…@patient.mssante.fr` en clair.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — imputabilité PGSSI-S
- **Exigences DSR honorées** : PGSSI-S, référentiel d'imputabilité (traçabilité des accès aux
  données de santé) ; règle 14 de la forge
- **INS** : jamais tracée ni journalisée en clair. La consultation porte l'identifiant technique.
- **Authentification PS** : PSC. La trace porte le RPPS et le nom PSC.
- **Habilitations** : titulaire, délégataire et membre lisent tout le journal de la boîte (inchangé)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : lecture par personne, marquages, gestion des boîtes dans la boîte visée, refus
  complets, actes système. Conservation 3 653 jours.
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — journal Postgres de la plateforme
- **AIPD / impact RGPD** : à mettre à jour — volume de traces de lecture accru, et IP, navigateur et
  identifiant visibles des co-utilisateurs (décision humaine)
