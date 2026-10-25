# todo-task-400.md — Délégation de BAL : tracer qui agit dans quelle BAL, et le montrer au délégant

**Repos**: dtos-mss, api-mail, client-angular
**Dependencies**: task-397 (actes délégués et audit réduit de la règle 14)
**Epic**: E009
**Single frontend**: true — la consultation du journal n'existe que dans weda2. Le mobile n'a pas
d'écran Audit, et cette task n'en crée pas (décision 1).
**Priorité**: **3** — un délégataire agit déjà dans la BAL de son délégant (task-397). Mailiz rend
le délégant **responsable** des accès qu'il ouvre, mais il ne voit aucun de ces actes. Rien ne
désigne non plus la **personne** qui a agi.

> **Analyse** : [Docs/audits/delegation-bal-mailiz-analyse-20261025.md](../Docs/audits/delegation-bal-mailiz-analyse-20261025.md)
> (§3.1 D4, §5 Q4).
> **Règle 14** (CLAUDE.md) : l'audit est la seule exception à « rien de persisté », réduit à
> l'action, l'auteur, le dossier, l'UID et le `Message-ID`.

## Ce qui est établi

- **Journal mutualisé** (ADR-2026-09-14) : table `audit_traces` du registre commun, partitionnée
  par mois.
  - Conservation : **3 653 jours** pour la famille `HealthDataAccess`, 365 jours pour la famille
    `Technical` (`AuditRetentionPolicy`).
  - Purge planifiée et globale.
- **Une trace appartient à un tenant** (compte × BAL), estampillé à l'émission. `user_id` est une
  **adresse de BAL**, pas une personne.
  - Le RPPS et l'identité PSC transitent sans être persistés (`MssAuditTrace.TransportMssRpps`,
    `TransportEmail`, `[NotMapped]`).
  - Aucune décision documentée n'interdit de les persister : c'est un choix de transport.
- **Consultation** : `GET /api/v1/audit/traces` et `GET /audit/traces/{id}`, limités au tenant de
  la session (`AuditController`). weda2 a un écran Audit (`libs/mss/src/features/audit` : liste,
  filtres, détail, chronologie). Le mobile n'en a pas.
- **Constat du 2026-10-25** : les lectures et suppressions de Cyril dans la BAL de Virginie sont
  tracées dans **le tenant de Cyril**, avec `user_id` = son adresse. Virginie n'en voit rien.

## Décisions actées (humain, 2026-10-25)

1. **Le délégant consulte les actes de ses délégataires dans weda2**, dans l'écran Audit existant,
   avec un filtre « actes de mes délégataires ». Pas d'écran sur le mobile.
2. **La personne qui agit est identifiée par son RPPS et son nom**, issus de PSC, enregistrés dans
   la trace.
3. **Une trace, deux lecteurs** : l'acte délégué est visible du délégataire (c'est son acte) et du
   délégant (c'est sa BAL).

## Objective

Tout acte fait dans une BAL déléguée est tracé avec trois choses : **qui** (RPPS et nom), **depuis
quelle BAL** (celle du délégataire) et **dans quelle BAL** (celle du délégant). Le délégant le voit
dans le journal de weda2, aux côtés de ses propres actes ; le délégataire aussi, dans le sien.

## Règles

- **Champs ajoutés à toute trace** :
  - la **personne qui agit**, RPPS et nom, pris dans l'identité PSC de la session ;
  - la **BAL propriétaire** : l'adresse du délégant pour un acte sur `shared/<adresse>/…`,
    sinon la BAL de la session.

  Ils sont renseignés pour **toutes** les traces nouvelles, déléguées ou non, pour qu'un journal ne
  mélange pas deux formats. Les traces antérieures restent sans ces champs : pas de reprise.
- **Acte délégué** : une trace dont la BAL propriétaire diffère de la BAL de la session.
- **Contenu d'une trace déléguée** (règle 14) : action, date, succès ou échec, personne qui agit,
  BAL du délégataire, BAL propriétaire, dossier, UID, `Message-ID`. **Jamais** objet,
  correspondants, INS, nom de patient ni contenu.
- **Lecture du journal** :
  - le **délégataire** voit ses traces comme aujourd'hui (son tenant), actes délégués compris,
    marqués « dans la BAL de `<adresse>` » ;
  - le **délégant** voit ses traces **et** celles dont la BAL propriétaire est la sienne, quel que
    soit le tenant qui les a émises ;
  - ces dernières sont marquées « par `<nom>` (RPPS `<n°>`), délégation ».
- **Délégant pas encore utilisateur** : la trace est rattachée à son **adresse**, pas à un tenant.
  Il la verra en se connectant pour la première fois. Rien n'est créé à son nom avant.
- **Filtre « actes de mes délégataires »** dans l'écran Audit de weda2, combinable avec les filtres
  existants (période, action).
- **Délégation retirée** : les traces passées **restent** visibles du délégant pendant toute leur
  durée de conservation. C'est le rôle même du journal.
- **Conservation** : famille `HealthDataAccess` pour les actes délégués de lecture, déplacement,
  suppression et envoi, soit 3 653 jours.
- **Cloisonnement** : un utilisateur ne voit jamais les traces d'une BAL qui n'est ni la sienne ni
  déléguée vers lui. Il ne voit pas non plus les actes **d'autres** délégataires dans une BAL qui
  lui est déléguée : seul le délégant voit tous les délégataires.

## Definition of Done

- [ ] Migration du registre : colonnes « RPPS de la personne qui agit », « nom de la personne qui
      agit » et « BAL propriétaire » sur `audit_traces`, nullables pour les traces antérieures.
      Index adapté à la lecture par BAL propriétaire et date. Audit de migration (règle 7c), sans
      effet sur les partitions existantes.
- [ ] `dtos-mss` : le contrat de trace expose la personne qui agit, la BAL propriétaire et
      l'indicateur « acte délégué ». Paquet publié, consommateurs .NET mis à jour, types
      TypeScript de weda2 alignés.
- [ ] Test d'intégration de bout en bout (banc de délégation de task-397) : B lit, puis supprime un
      message de `shared/<A>`. Lu dans la réponse réelle, vu rouge (règle 1b) :
      - `GET /audit/traces` de **A** renvoie ces deux traces avec le RPPS et le nom de B et la BAL
        propriétaire = A ;
      - `GET /audit/traces` de **B** les renvoie aussi, marquées « dans la BAL de A ».
- [ ] Test d'intégration : A n'a encore jamais utilisé l'application. B agit, puis A se connecte et
      attache sa BAL : `GET /audit/traces` de A renvoie les actes de B.
- [ ] Test d'intégration — cloisonnement : avec C également délégataire de A, B ne voit pas les
      traces de C. Un utilisateur tiers D ne voit aucune trace de A.
- [ ] Test d'intégration : la délégation de B est retirée ; A voit toujours les traces passées de B.
- [ ] Test d'intégration : une trace déléguée ne contient ni objet, ni correspondants, ni INS, ni
      nom de patient (règle 14).
- [ ] Test d'intégration : le filtre « actes de mes délégataires » ne renvoie que les traces dont la
      BAL propriétaire est celle de la session et dont la personne qui agit est un autre RPPS.
- [ ] Test unitaire : la famille de conservation des actes délégués est `HealthDataAccess`.
- [ ] Tests de composants weda2 :
      - filtre « actes de mes délégataires » ;
      - mention « par `<nom>` (RPPS `<n°>`), délégation » dans la liste et le détail ;
      - mention « dans la BAL de `<adresse>` » pour le délégataire ;
      - chronologie inchangée pour une trace non déléguée.
- [ ] Scénario **E2E-DELEG-008** ajouté dans `Api/Mail/e2e/scenarios.yml`, et implémenté dans weda2 :
      « le délégant voit, dans son journal, les actes faits dans sa BAL par son délégataire ».
      Clients : `mobile: non-applicable — l'application mobile n'a pas d'écran de journal d'audit`,
      `angular: requis`.
- [ ] Aucun RPPS ni nom dans les journaux applicatifs (Seq) : ils ne vivent que dans la trace
      d'audit.
- [ ] Build et tests verts : dtos-mss, api-mail, client-angular ; `/e2e` vert, avec parité verte.

## Manual Test Plan

Comptes de formation : Cyril, délégataire de Virginie.

1. Se connecter en **Cyril** sur weda2 par PSC. Dans la boîte déléguée de Virginie, ouvrir un
   message, puis en supprimer un autre.
2. Ouvrir l'écran Audit de Cyril : ses deux actes y figurent, marqués « dans la BAL de
   virginie.medecinrpps0062267@… », sans objet ni données patient.
3. Se connecter en **Virginie** sur weda2. Dans l'écran Audit, activer « actes de mes
   délégataires » :
   - les deux actes de Cyril apparaissent, « par Cyril … (RPPS 899700723440), délégation » ;
   - désactiver le filtre : ils apparaissent parmi ses propres actes, dans l'ordre chronologique.
4. Virginie retire la délégation dans le webmail Mailiz. Son écran Audit montre toujours les actes
   passés de Cyril.
5. Vérifier dans Seq qu'aucun RPPS ni nom n'apparaît dans les journaux applicatifs de ces actes.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — fonctionnalité Mailiz sans exigence DSR publiée
- **Exigences DSR honorées** : non applicable. La PGSSI-S (imputabilité, journalisation) est suivie :
  chaque acte sur des données de santé est rattaché à une personne identifiée.
- **INS** : non applicable — jamais dans une trace déléguée (règle 14)
- **Authentification PS** : inchangée. L'identité tracée vient de la session PSC / e-CPS du
  délégataire.
- **Habilitations** : lecture du journal limitée à sa propre BAL, aux BAL qui vous sont déléguées
  (vos propres actes seulement), et, pour le délégant, à tous les actes faits dans sa BAL.
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : **objet de la task**. L'imputabilité est rendue explicite (RPPS et nom de la
  personne qui agit) et la BAL concernée est identifiée. Conservation 10 ans pour les accès aux
  données de santé. Les journaux sont consultables par le titulaire de la BAL.
- **Consentement patient** : non applicable
- **Référentiels métier** : RPPS (identifiant national des professionnels)
- **Hébergement HDS** : oui — registre commun, déjà hébergé
- **AIPD / impact RGPD** : **à mettre à jour**.
  - Donnée personnelle nouvelle dans le journal : RPPS et nom de la personne qui agit, sur une base
    légale d'obligation de traçabilité.
  - Communiquée au délégant, responsable de la délégation.
  - Conservation 10 ans.

  À joindre à la mise à jour ouverte par task-397.

## Notes de cadrage

- **Points de code** :
  - estampillage des traces : `AuditService.cs:86-102` ;
  - colonnes persistées : `PostgresAuditSink.cs:58-65` ;
  - champs de transport : `MssAuditTrace.cs:27-33` ;
  - lecture par tenant : `AuditController` et `auditReader`.

  La lecture du délégant ajoute « ou BAL propriétaire = ma BAL » à la requête.
- **Tenant multiple** : une même adresse peut avoir plusieurs tenants (BAL organisationnelle,
  `RegistryTenant.cs:13-24`). La lecture par BAL propriétaire porte sur l'**adresse**, ce qui les
  couvre tous. La délégation Mailiz ne concerne que les BAL personnelles (PER).
- **Hors périmètre** :
  - écran de journal sur le mobile ;
  - notification au délégant à chaque acte ;
  - export du journal ;
  - accès d'administration et de sécurité au journal (task-302).
