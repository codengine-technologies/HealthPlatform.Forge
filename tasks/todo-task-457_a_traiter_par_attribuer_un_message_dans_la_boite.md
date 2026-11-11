# todo-task-457.md — « À traiter par » : attribuer un message dans la boîte

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Dependencies**: done-task-454 (état « traité »)
**Epic**: E024
**Priorité**: EPIC E024, demandée par l'humain le 2026-11-11. L'accès partagé est fait (douleur n° 6 : 5/5) ; il
manque le **travail à plusieurs dans la boîte**. Le pré-tri par le secrétariat est le levier le mieux documenté
(Michigan : −16 % de messages par médecin, −62 % de doublons ; tri administratif britannique : jusqu'à −80 % de
courrier sur le bureau du médecin).

> **Origine.** Analyse du 2026-11-11, manques C1 et C2. Demande explicite de l'humain du 2026-11-11 : « indiquer *à
> traiter par* : choisir le médecin affecté ou la secrétaire, pour que le message lui soit attribué ».

## Ce qui est établi

- **Aucun modèle ni endpoint d'attribution.**
- **Aucun endpoint ne liste les personnes rattachées à une boîte** : `/api/v1/account/mailboxes*` ne rend que les
  boîtes de l'utilisateur.
- La liste existe dans le registre commun : `RegistryTenantRow` (`MailboxId`, `Role`, `PersonFirstName/LastName`,
  `State`), lu par `PostgresTenantRegistryClient`.
- La base de la boîte ne connaît que le `sub` de la personne (`User.AuthenticationSubject`), sans nom ni RPPS. Les
  auteurs sont **dénormalisés** sur chaque ligne (`ActorNames`, comme `BiologyAck.CreatedBy*`).
- `NewMailNotifier` tourne en tâche de fond **sans personne** : il lit les réglages de la ligne boîte. Une notification
  destinée à une personne précise demande une résolution par personne.
- Rôles affichables : `MailboxRole` / `MAILBOX_ROLE_LABELS` (Titulaire, Membre, Délégation), `actorWithRole`
  (weda2).

## Objective

Sur n'importe quel message, une personne de la boîte indique **« À traiter par »** et choisit une personne rattachée à
cette boîte : le médecin titulaire, un confrère membre, la secrétaire délégataire. Le message lui est **attribué**. Il
apparaît dans sa vue **« Pour moi »**, et elle en est avertie.

Règles :
- **Choisir la personne** : la liste des personnes rattachées à la boîte et actives (verdict de l'opérateur valide),
  avec nom et rôle (« Dr Virginie MARTIN — titulaire », « Cyril DELEGUE — délégataire »). On ne saisit jamais un nom
  libre.
- **Une seule personne attribuée à la fois.** On peut réattribuer ou retirer l'attribution. Chaque geste est imputé.
- **Affichage** : « À traiter par {Prénom NOM} — attribué par {Prénom NOM} le … », sur la ligne (une pastille avec les
  initiales) et dans le détail.
- **Vue « Pour moi »** : les messages attribués à la personne connectée et non traités, avec un compteur. Sur weda2,
  dans l'arborescence au-dessus des vues par nature ; sur mobile, en puce et en tuile d'Accueil (flag
  `dashboard_widget_for_me`).
- **Avertir** : la personne attribuée reçoit une notification dans l'application, en direct si elle est connectée,
  sinon à sa prochaine ouverture (« Cyril DELEGUE vous a attribué un message »). Le contenu clinique n'est jamais dans
  la notification.
- **Traiter clôt l'attribution** : quand quelqu'un marque le message traité (task-454), il sort de « Pour moi ». Le
  détail garde « Attribué à … — traité par … ».
- **Une personne qui perd l'accès** (révocation, refus de l'opérateur) n'est plus proposée. Ses attributions en cours
  s'affichent « À traiter par {nom} (accès retiré) » et restent visibles dans « À traiter » de la boîte.
- **Groupé** : attribuer une sélection en une fois (weda2 et mobile).
- **Ancrage** selon task-453.

### Hors périmètre

- Attribution automatique par règle (ex. tout le « Pour info » à la secrétaire).
- Notes internes : task-458.
- Détection de collision (« Cyril rédige déjà une réponse »).

## Definition of Done

- [ ] Endpoint des personnes rattachées à la boîte (registre commun), limité aux personnes actives, accessible
      seulement aux personnes de cette boîte sous verdict valide.
- [ ] Attribution stockée dans la base de la boîte, ancrée selon l'ADR de task-453 ; migration FluentMigrator, audit
      (règle 7c).
- [ ] Contrat : personne attribuée, auteur et date dans `MailDto` ; vue « Pour moi » et compteur ; paquet DTO publié.
- [ ] Actes d'audit `MailAssigned`, `MailUnassigned` en fin de `AuditActionType`, miroirs TypeScript,
      `HealthDataAccess`.
- [ ] Notification ciblée sur **la personne attribuée** (pas sur la ligne boîte) : la résolution par personne est
      ajoutée et testée.
- [ ] Tests unitaires : attribuer, réattribuer, retirer, traiter clôt l'attribution, personne sans accès non proposée,
      attribution d'une personne qui a perdu l'accès.
- [ ] **Test d'intégration de bout en bout (règle 1b), deux personnes sur la même boîte** (règle 14), sur
      `PUT api/v1/Mail/emails/{id}/assignee` :
      - le titulaire attribue au délégataire ; le délégataire relit le message dans « Pour moi » ;
      - la trace porte le titulaire comme auteur et le délégataire comme objet ;
      - le délégataire traite, le message sort de « Pour moi » ;
      - cas d'échec : personne non rattachée à la boîte → 400 en `ProblemDetails`, rien n'est écrit.
      Vu rouge.
- [ ] Test d'intégration : une personne d'une **autre** boîte ne peut ni lister les personnes ni attribuer (403).
- [ ] Tests de composant (weda2 et mobile), vus rouges par mutation : sélecteur « À traiter par », pastille, vue et
      compteur « Pour moi », notification, attribution groupée.
- [ ] **Scénarios e2e**, mobile et angular requis, vus rouges :
      - `E2E-ASSIGN-001` v1 : le titulaire attribue un message à la secrétaire délégataire, qui le trouve dans « Pour
        moi » ;
      - `E2E-ASSIGN-002` v1 : traiter un message attribué le retire de « Pour moi » et affiche « traité par ».
- [ ] `data-testid`, conventions de libellés, aucune donnée de santé dans la notification ni les logs.
- [ ] Build et tests verts (api-mail, Dtos, weda2, mobile) ; client-angular : code-only.

## Manual Test Plan

1. Boîte du médecin avec un délégataire secrétaire rattaché (environnement de formation). Titulaire sur weda2,
   secrétaire sur le mobile.
2. Titulaire : sur un courrier, « À traiter par » → la liste montre la secrétaire et le titulaire, avec leurs rôles.
   Choisir la secrétaire.
3. Mobile, secrétaire : la notification « Dr … vous a attribué un message » arrive ; la puce « Pour moi » compte 1.
4. Secrétaire : marquer le message traité. Titulaire : le détail dit « Attribué à … — traité par … ».
5. Attribuer trois messages d'un coup depuis la sélection groupée de weda2.
6. Révoquer la délégation chez l'opérateur : la secrétaire n'est plus proposée ; ses attributions en cours affichent
   « (accès retiré) ».

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — organisation du travail en cabinet
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel ; secrétaire par e-CPS (RPPS+)
- **Habilitations** : seules les personnes rattachées à la boîte, sous verdict récent de l'opérateur, sont proposées et
  peuvent attribuer (règle 14) ; le rôle vient du rattachement (Annuaire Santé)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : `MailAssigned`, `MailUnassigned` au nom de la personne qui agit, avec la personne attribuée en
  objet ; `HealthDataAccess`, 3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — base de la boîte et registre commun
- **AIPD / impact RGPD** : à mettre à jour — la liste des personnes d'une boîte est visible de chacune d'elles, et les
  attributions révèlent la répartition du travail
