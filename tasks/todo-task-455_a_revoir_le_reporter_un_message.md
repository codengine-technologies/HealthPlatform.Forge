# todo-task-455.md — « À revoir le… » : reporter un message

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Dependencies**: done-task-454 (état « traité » et vue « À traiter »)
**Epic**: E024
**Priorité**: EPIC E024, demandée par l'humain le 2026-11-11. Douleur n° 7 (2/5). Remettre un mail à plus tard est
quotidien, et faute de mieux on le repasse en « non lu » (Sarrafzadeh, Microsoft, 2019).

> **Origine.** `Docs/analyse-fonctionnelle-manques-messagerie-2026-11.md`, manque A2 (HEY « Bubble Up »,
> Nextcloud, Superhuman). Exemple clinique : « contrôler l'INR dans 3 jours ».

## Ce qui est établi

- **Aucun report n'existe**, ni ordonnanceur durable : pas de Hangfire, pas de Quartz, pas de messages différés
  MassTransit. `IBackgroundTaskQueue` est en mémoire.
- La synchro ne tourne que sur un geste du praticien, avec une session PSC. Rien ne parcourt les boîtes sans
  praticien connecté.
- Conséquence retenue : la réapparition se fait **à la lecture** (un message reporté redevient visible quand sa date
  est passée). Aucune tâche planifiée n'est nécessaire.
- `NewMailNotifier` tourne en tâche de fond et lit les réglages de la **ligne boîte**, pas ceux de la personne.

## Objective

Le praticien reporte un message à une date : il **disparaît** de « À traiter » et **revient en tête** à cette date,
signalé « Revenu — reporté par {nom} le … ».

Règles :
- **Choix rapides** : « Ce soir 18 h », « Demain 8 h », « Dans 3 jours », « Lundi 8 h », « Choisir une date… ». Fuseau
  Europe/Paris. Une date passée est refusée.
- **Où** : panneau « Actions & dossier » et sélection groupée sur weda2 ; balayage « Plus tard » en deuxième position
  et détail sur mobile.
- **Pendant le report** : le message sort de « À traiter » et des vues d'étiquettes. Une vue « Reportés » liste les
  messages en attente, avec leur date de retour. On peut les rappeler tout de suite (« Revoir maintenant ») ou changer
  la date.
- **Au retour** : le message réapparaît **en tête** de « À traiter », marqué non lu, avec le bandeau « Revenu —
  reporté par {Prénom NOM} le {date} ». Une notification dans l'application signale le retour à la prochaine
  ouverture, ou en direct si la personne est connectée.
- **Boîte partagée** (règle 14) : le report appartient à la boîte et s'affiche avec son auteur (« Reporté au 15/11 par
  Cyril DELEGUE (délégataire) »). Traiter le message annule le report.
- **Annulation** : toast « Reporté au … — Annuler » pendant 6 s.
- **Ancrage** selon task-453 : un report survit à un déplacement hors plateforme.

### Hors périmètre

- Les notifications push : la réapparition est vue dans l'application (analyse, vague « à instruire »).
- Le report d'un message envoyé en attente de réponse : task-462.

## Definition of Done

- [ ] Contrat : date de retour et auteur du report dans `MailDto` ; vue « Reportés » ; compteur. Paquet DTO publié.
- [ ] Migration FluentMigrator (base de la boîte), ancrage selon l'ADR de task-453, audit de migration (règle 7c).
- [ ] Actes d'audit `MailSnoozed`, `MailSnoozeCancelled`, plus un acte système « retour d'un report » ; miroirs
      TypeScript ; famille `HealthDataAccess`.
- [ ] Tests unitaires : choix rapides (dont « Lundi 8 h » un lundi après 8 h, et le passage à l'heure d'hiver), date
      passée refusée, retour en tête, traiter annule le report.
- [ ] **Test d'intégration de bout en bout (règle 1b)** pour `PUT api/v1/Mail/emails/{id}/snooze` :
      - avant l'échéance, le message est absent de « À traiter » et présent dans « Reportés » ;
      - après l'échéance (horloge du test avancée par `TimeProvider`), il revient en tête, non lu, avec l'auteur du
        report ;
      - cas d'échec : date passée → 400 en `ProblemDetails`.
      Vu rouge.
- [ ] **Deux personnes sur la même boîte** : le délégataire reporte ; le titulaire voit « Reporté par » le délégataire ;
      trace au nom du délégataire.
- [ ] Tests de composant (weda2 et mobile), vus rouges par mutation : choix rapides, date personnalisée, vue
      « Reportés », « Revoir maintenant », bandeau de retour, annulation.
- [ ] **Scénarios e2e**, mobile et angular requis, vus rouges :
      - `E2E-TRIAGE-003` v1 : reporter un message le retire de « À traiter » et le place dans « Reportés » ;
      - `E2E-TRIAGE-004` v1 : un message dont le report est échu (seed `mail-report-echu`, ajouté aux données)
        revient en tête avec le bandeau « Revenu ».
- [ ] `data-testid`, conventions de libellés, aucune donnée de santé dans les libellés ni les logs.
- [ ] Build et tests verts (api-mail, Dtos, weda2, mobile) ; client-angular : code-only.

## Manual Test Plan

1. Backend, weda2 et mobile lancés comme pour task-454.
2. weda2 : reporter un message à « Choisir une date » dans 2 minutes : il disparaît de « À traiter » et apparaît dans
   « Reportés » avec l'heure de retour.
3. Attendre 2 minutes, actualiser : il revient en tête, non lu, avec « Revenu — reporté par {votre nom} ».
4. Mobile : balayer un message, choisir « Plus tard » puis « Demain 8 h », puis « Annuler » dans le toast : il reste
   dans « À traiter ».
5. Délégataire : reporter un message ; titulaire : la vue « Reportés » le montre, avec le nom du délégataire.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — organisation du travail
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel
- **Habilitations** : titulaire, membre, délégataire, sous verdict récent de l'opérateur (règle 14)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : `MailSnoozed`, `MailSnoozeCancelled` au nom de la personne ; retour d'un report en acte système ;
  `HealthDataAccess`, 3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — base de la boîte
- **AIPD / impact RGPD** : inchangé par rapport à task-454 (même nature de donnée : auteur d'un geste de travail)
