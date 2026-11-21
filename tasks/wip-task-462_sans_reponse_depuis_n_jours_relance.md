# todo-task-462.md — Sans réponse depuis N jours : relance

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Reprises**: 4
**Dependencies**: done-task-454 (vue « À traiter »), done-task-459 (détection des réponses, rapports exclus)
**Epic**: E024
**Priorité**: EPIC E024, demandée par l'humain le 2026-11-11. Douleur n° 5 (2/5). Une demande d'avis restée sans
réponse est une boucle de coordination non fermée, donc un risque de soins.

> **Décision humaine du 2026-11-20 (au `/start`).** La dépendance à task-460 (suivi d'acheminement, supprimée le
> 2026-11-13 sans avoir été faite) est retirée. Ce qu'elle apportait existe en partie : rapports exclus (task-459),
> état « non distribué » dans la conversation (task-487). La règle « Échec de remise » est réécrite en conséquence.

> **Origine.** Analyse du 2026-11-11, manque A3 (Superhuman « Remind me », Gmail « Nudges », Nextcloud « follow-up »,
> renvoi automatique de Lifen ; « dialogmelding » norvégien avec un délai de réponse attendu).

## Ce qui est établi

- La détection d'une réponse est posée par task-459 : `In-Reply-To` et `References`, accusés et rapports exclus.
- La synchro ne tourne que sur un geste du praticien, avec une session PSC. Une réponse déjà arrivée mais pas encore
  synchronisée donnerait une **fausse relance**.
- Aucun ordonnanceur durable. La réapparition se fait **à la lecture**, comme pour le report de task-455.

## Objective

En envoyant un message, le praticien demande **« Me rappeler si pas de réponse sous… »**. Si aucune réponse n'arrive à
temps, le message envoyé revient dans **« À traiter »** : « Sans réponse de {destinataire} depuis {N} jours », avec deux
gestes, **Relancer** et **Clore**.

Règles :
- **À l'envoi** : choix « 3 jours », « 7 jours », « 14 jours », « Choisir une date… », ou aucun rappel (par défaut).
  Disponible dans la rédaction weda2 et mobile.
- **Après l'envoi** : le rappel se pose aussi depuis le détail d'un message envoyé.
- **Une réponse de n'importe quel destinataire** clôt le rappel d'elle-même. Le détail l'indique : « Rappel clos —
  réponse reçue le … ».
- **Pas de fausse relance** : le rappel ne réapparaît qu'après une synchronisation postérieure à l'échéance.
- **Au retour** :
  - le message envoyé apparaît en tête de « À traiter » avec le bandeau « Sans réponse de Dr X depuis 7 jours —
    demandé par {Prénom NOM} » ;
  - **Relancer** ouvre une réponse aux mêmes destinataires, objet « Relance : … », message d'origine cité ; à l'envoi,
    un nouveau rappel de même durée est proposé ;
  - **Clore** arrête le rappel. Le geste est imputé.
- **Échec de remise** : un envoi marqué « non distribué » par un rapport d'échec (`ReportKind`, task-487) ne pose pas
  de rappel, et un rappel déjà posé se clôt (acte système). Rien n'est promis dans « À traiter » pour l'échec
  lui-même : task-460, qui l'y aurait rangé, a été retirée.
- **Boîte partagée** : le rappel appartient à la boîte et affiche qui l'a demandé (règle 14).
- **Ancrage** selon task-453.

**Décisions humaines du 2026-11-20** (arbitrages AH1 à AH3 de la revue, recommandations acceptées) :
- **AH1** — seules les réponses et les échecs de remise arrivés **après la demande** du rappel le clôturent. Le repère
  de la Boîte de réception est l'`UIDNEXT` relevé à la demande ; pour un rappel posé à l'envoi, il est relevé **avant**
  l'envoi SMTP. Une réponse antérieure à la demande ne clôt pas le rappel.
- **AH2** — une réponse automatique (`Auto-Submitted`, message automatique de task-456) ne clôt pas le rappel ; seule
  compte la réponse d'un destinataire de l'envoi (À ou Cc).
- **AH3** — un échec de remise ne clôt le rappel que si **tous** les destinataires sont en échec.

## Definition of Done

- [ ] Rappel stocké dans la base de la boîte (échéance, demandeur), ancré selon l'ADR de task-453 ; migration
      FluentMigrator, audit règle 7c.
- [ ] Contrat : option à l'envoi (`MailDto`), état du rappel sur l'envoi, gestes « Clore » et « Relancer » ; paquet
      DTO publié.
- [ ] Actes d'audit `FollowUpRequested`, `FollowUpClosed` (personne) ; clôture sur réponse et retour en actes système.
- [ ] Tests unitaires : échéance atteinte sans réponse, réponse avant l'échéance, réponse par `References` seul,
      accusé de lecture qui ne clôt pas, envoi en échec sans rappel, aucun retour avant une synchro postérieure à
      l'échéance, « Relancer » préparé avec les bons destinataires.
- [ ] **Test d'intégration de bout en bout (règle 1b)** :
      - envoi avec rappel à 3 jours, horloge avancée par `TimeProvider`, synchro : l'envoi est lu dans « À traiter »
        avec le bandeau et le demandeur ;
      - cas nominal inverse : une réponse injectée avant l'échéance clôt le rappel ;
      - cas d'échec : une échéance passée à la demande → 400 en `ProblemDetails`.
      Vu rouge.
- [ ] **Deux personnes sur la même boîte** : le délégataire demande le rappel, le titulaire le voit revenir avec
      « demandé par » le délégataire.
- [ ] Tests de composant (weda2 et mobile), vus rouges par mutation : option à l'envoi, bandeau, Relancer, Clore.
- [ ] **Scénario e2e** `E2E-FOLLOWUP-001` v1, mobile et angular requis, vu rouge : un envoi dont le rappel est échu
      (donnée de seed `envoi-rappel-echu`, ajoutée aux données) revient dans « À traiter » avec « Sans réponse », et
      « Clore » le retire.
- [ ] `data-testid`, conventions de libellés, aucune donnée de santé dans les libellés ni les logs.
- [ ] Build et tests verts (api-mail, Dtos, weda2, mobile) ; client-angular : code-only.

## Manual Test Plan

1. Backend, weda2 et mobile sur la boîte de formation, avec une seconde boîte de test comme destinataire.
2. Envoyer une demande d'avis avec « Me rappeler si pas de réponse sous : Choisir une date » dans 3 minutes.
3. Attendre 3 minutes, synchroniser : l'envoi apparaît dans « À traiter » avec « Sans réponse de … depuis … ».
4. « Relancer » : une réponse préremplie « Relance : … » s'ouvre. L'envoyer.
5. Depuis la seconde boîte, répondre à la relance ; synchroniser : le rappel est clos, « réponse reçue le … ».

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (coordination des soins)
- **Vague Ségur** : hors Ségur
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel ; la relance est un envoi MSSanté ordinaire
- **Habilitations** : personnes de la boîte sous verdict de l'opérateur (règle 14)
- **Interop CI-SIS** : non applicable — RFC 5322 (`In-Reply-To`, `References`)
- **Tracé PGSSI-S** : `FollowUpRequested`, `FollowUpClosed` au nom de la personne ; clôture sur réponse en acte
  système ; la relance est tracée comme un envoi (`MailReply`) ; `HealthDataAccess`, 3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — base de la boîte
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : feat/task-462-sans-reponse-depuis-n-jours-relance — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-462-sans-reponse-depuis-n-jours-relance
- `client-mobile` (pushed) : feat/task-462-sans-reponse-depuis-n-jours-relance — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-462-sans-reponse-depuis-n-jours-relance
- `dtos-mss` (paresseuse) : aucune branche au /start — créée par /develop au premier contrat touché
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (`feature/nova-mss-weda-integration` au /start) — humain gère branche, commit, push, PR TFS

## Develop log

### Arbitrage préalable

- **task-460 absente** (dépendance déclarée) : décision humaine du 2026-11-20, « Retirer la dépendance » — la règle
  « Échec de remise » est réécrite dans l'Objectif (commit `671772a`). Rien n'est promis dans « À traiter » pour l'échec
  de remise lui-même.

### Conception

- **Ancrage** (ADR task-453) : le rappel est une ligne `mail_follow_ups` de la base de la boîte, ancrée par le
  `Message-ID` de l'envoi (aucune clé étrangère vers une ligne de message). Il survit à un déplacement hors de la
  plateforme : le retour relit la copie rangée ailleurs (test d'intégration n° 5).
- **Contrat** (dtos-mss 630.0.0) : `MailDto.FollowUpDueAt` (option à l'envoi), `MailDto.FollowUp` (`MailFollowUpDto` :
  échéance, demandeur, destinataire attendu, ouvert / revenu / clos, motif, auteur et instant de clôture, arrivée de
  la réponse), `SaveDraftDto` / `DraftDto.FollowUpDueAt`, actes `FollowUpRequested` (77), `FollowUpClosed` (78),
  `FollowUpReturned` (79).
- **Routes** : `PUT` / `DELETE folders/{dossier}/emails/{uid}/follow-up` (poser depuis le détail, « Clore »),
  `GET follow-ups/returned` (les envois revenus, à placer en tête de « À traiter »). Erreurs en `ProblemDetails`
  (échéance passée ou au-delà d'un an → 400, message reçu → 400, sans rappel → 404).
- **Pas de fausse relance** : le retour n'est calculé qu'en ligne, et seulement quand la Boîte de réception est
  entièrement ingérée (plus grand UID ingéré ≥ plus grand UID annoncé par le serveur IMAP). Une réponse — par
  `In-Reply-To` ou par `References` seul — clôt le rappel en acte système ; un accusé de lecture ou un rapport de
  distribution n'est jamais une réponse ; un rapport d'échec de remise clôt le rappel (acte système). Horloge par
  `TimeProvider`.
- **Imputation (règle 14)** : `FollowUpRequested` et `FollowUpClosed` au nom de la personne (RPPS, nom PSC, rôle) ;
  le retour et la clôture sur réponse ou échec de remise en actes système. Le rappel appartient à la boîte : le
  demandeur est affiché (« demandé par Prénom NOM »).
- **Relancer** : une réponse aux mêmes destinataires (À et Cc), objet « Relance : … » (jamais empilé), message cité ;
  le délai du rappel relancé est reproposé ; l'envoi de la relance clôt le rappel précédent (motif « relancé »).
- **Compteur** : les envois revenus entrent dans le compteur « À traiter » de la Boîte de réception.
- **Clients** : weda2 et mobile — choix à la rédaction (aucun, 3, 7, 14 jours, date), qui suit le brouillon ;
  bandeau du détail (revenu : Relancer / Clore ; en cours ou clos : son état ; envoyé sans rappel : « Me rappeler ») ;
  marque « Sans réponse » sur la ligne ; envois revenus en tête de la page 1 de « À traiter » de la Boîte de réception,
  désignés par (dossier, UID) — les UID d'Envoyés recoupent ceux de la Boîte de réception.

### Commits

| Repo | Commit | Objet |
|---|---|---|
| dtos-mss | `d668837` | contrat du rappel, publié 630.0.0 par la CI |
| api-mail | `eec9058f` | bump `HealthPlatform.Dtos.Mss` 630.0.0 |
| api-mail | `6d78f13b` | rappel « sans réponse », retour dans « À traiter » |
| api-mail | `963a6c26` | passe qualité (/simplify) |
| api-mail | `f8678551` | le manifeste e2e désigne le rappel revenu par (dossier, uid) |
| client-mobile | `fc0a981` | rappel à la rédaction, bandeau, Relancer / Clore, marque, tête de « À traiter » |
| plan de contrôle | `480fcbd` | `contract_impact` cherche la surface sur develop ET sur la branche — **local, non poussé : relecture humaine (règle d'or 7)** |

### Preuves (règle 1b, tests vus rouges)

**api-mail — intégration de bout en bout** (`FollowUpEndToEndTests`, vraie pile HTTP, Dovecot, PostgreSQL ; 12
mutations, toutes rouges, restauration verte 5/5) :

| Mutation | Test rouge |
|---|---|
| M1 rappel non posé à l'envoi | 3 tests (retour, réponse avant échéance, copie déplacée) |
| M2 boîte réputée synchronisée sans ingestion | réponse avant échéance / pas de fausse relance |
| M3 `References` ignoré | réponse avant échéance |
| M4 accusé de lecture compté comme réponse | retour après échéance |
| M5 retour tracé au nom de la personne | retour après échéance (acte système attendu) |
| M6 demandeur non recopié | retour après échéance (« demandé par » le délégataire, lu par le titulaire) |
| M7 échéance passée acceptée | 400 `ProblemDetails` (détail et envoi) |
| M8 rappel accepté sur un message reçu | 400 sur un message reçu |
| M9 copie rangée ailleurs ignorée | rappel survivant au déplacement |
| M10 « Clore » sans personne | retour puis « Clore » imputé |
| M11 compteur « À traiter » inchangé | retour après échéance |
| M12 échéance jamais atteinte | retour après échéance, copie déplacée |

**client-mobile — Karma** (mutations M1-M13, toutes rouges sur l'assertion visée, fichiers restaurés octet pour octet) :

| Mutation | Spec rouge |
|---|---|
| M1 bandeau revenu muet | détail : bandeau, « Clore », « Relancer » |
| M2 « Clore » ne pose pas le rappel clos | détail : « Clore » |
| M3 « Relancer » garde « Re: » | détail : « Relancer » |
| M4 « Relancer » oublie le délai | détail : « Relancer » |
| M5 « Me rappeler » absent sur un envoyé | détail : « Me rappeler » |
| M6 l'échéance ne part pas avec l'envoi | rédaction : sans choix / « 7 jours » |
| M7 le brouillon rouvert perd son rappel | rédaction : brouillon |
| M8 la relance ignore l'objet donné | rédaction : « Relancer » |
| M9 les rappels revenus ne passent pas en tête | état : tête de la page 1 (même UID qu'un message reçu) |
| M10 un rappel clos reste dans « À traiter » | état : rappel clos |
| M11 le choix « 7 jours » ne remonte pas | sélecteur |
| M12 « Relance : » empilé | utilitaire |
| M13 la page de détail n'adopte pas le rappel | page de détail (`mailUpdated$`) |

**client-angular (weda2) — Vitest** (W1-W14, toutes rouges sur assertion, pas sur la collecte ; lancées par
PowerShell, `--pool=forks`, une spec à la fois) :

| Mutation | Spec rouge |
|---|---|
| W1 bandeau revenu muet | bandeau : texte revenu |
| W2 « Clore » ne pose pas le rappel | bandeau : « Clore », « Me rappeler » |
| W3 « Relancer » garde « Re: » | détail : « Relancer » |
| W4 « Relancer » oublie le délai | détail : « Relancer » |
| W5 l'échéance ne part pas par la route des brouillons | rédaction : route des brouillons |
| W6 l'échéance ne part pas par l'envoi direct | rédaction : « 3 jours », aucun rappel par défaut |
| W7 le brouillon rouvert perd son rappel | rédaction : brouillon rouvert |
| W8 la relance ne repropose pas le délai | rédaction : « Relancer » |
| W9 les rappels revenus ne passent pas en tête | état : tête de la page 1 |
| W10 un rappel clos reste dans « À traiter » | état : rappel clos |
| W11 le choix « 7 jours » ne remonte pas | sélecteur |
| W12 « Relance : » empilé | utilitaire |
| W13 l'enrichissement refusionne par UID seul | liste : un envoi de même UID reste intact |
| W14 l'envoi revenu reste un squelette | ligne : « Sans réponse » au lieu d'un squelette |

**Scénario e2e E2E-FOLLOWUP-001 v1** (catalogue `Api/Mail/e2e/scenarios.yml`, mobile et angular requis, donnée de
seed `envoi-rappel-echu`) :

- **Mobile** (banc `--serve-only`, `--grep E2E-FOLLOWUP-001`) : **rouge** sous mutation « Clore sans effet » (aucun
  `DELETE …/follow-up` en 30 s, après la marque, la tête de liste et le bandeau vus) ; puis **rouge** une seconde fois
  sur le code restauré : « Clore » aboutissait côté serveur mais le bandeau restait affiché — la page de détail mobile
  n'adoptait de `mailUpdated$` que le bandeau « répondu » (task-459). Corrigé (`mail-detail.page.ts` adopte aussi le
  rappel), test de page ajouté et vu rouge (M13) ; **vert** sur un seed neuf (1 passed).
- **weda2** (banc `--serve-only`, marqueur de mutation prouvé servi dans les chunks, consigne « journal muet ») : le
  premier passage, mutation en place, a été **rouge trop tôt** — la marque « Sans réponse » n'apparaissait pas dans
  « À traiter ». Deux défauts, trouvés par le parcours :
  1. **fusion par UID seul** (antérieure à la task) : la page relue après enrichissement était refusionnée par
     `uid` ; Envoyés/1 était écrasé par Boîte de réception/1 (trace : `NG0955`, clé `INBOX\u00001` aux index 0 et 13).
     Corrigé dans `mail-list.component.ts` (enrichissement), `mss-mail.component.ts` (rafraîchissement du dossier) et
     `mail-state.service.ts` (`restoreMailsToList`) : clé `mailKeyString` (dossier, UID). Spec `mail-list` vue rouge (W13) ;
  2. **squelette** : un envoi n'est jamais enrichi dans la Boîte de réception (`enrichmentStatus` = Pending), et la
     ligne restait un squelette sans marque. Un envoi revenu n'est plus « en cours d'analyse »
     (`mail-header.component.ts`) ; spec `mail-header.follow-up` vue rouge (W14).
  Puis **rouge** au bon endroit sous mutation « Clore sans effet » (aucun `DELETE …/follow-up` en 30 s, après la
  marque, la tête de liste et le bandeau vus), et **vert** sur le code restauré (1 passed). Le premier montage du banc
  weda2 était tombé en outillage (« nx serve pas prêt après 480 s » : réoptimisation Vite concurrente du backend),
  rejoué une fois.

### Builds / tests

| Repo | Build | Tests |
|---|---|---|
| dtos-mss | vert | n/a |
| api-mail | vert | suite complète verte, rejouée sur `f8678551` : 8 279 tests, 0 échec, aucun crash ; marqueur vert `f8678551` |
| client-mobile | `npm run build` vert | Karma 1703/1703 (passe finale) ; marqueur vert `fc0a9817` |
| client-angular | `nx build weda2` vert | mss-lib 1 922/1 922, `nx test weda2` vert, ESLint 0 erreur (avertissements préexistants), `tsc` e2e 0, Prettier propre sur les fichiers propres à HEAD ; marqueur vert sur l'arbre final |

### Passe qualité (/simplify)

- **api-mail** : commit `963a6c26` (reuse, simplification), re-validé build + suite complète.
- **client-mobile** : extraction de `loadMailsByKeys` (hydratation par clés, partagée par « Pour moi » et les envois
  revenus) ; aucun autre cleanup retenu.
- **client-angular** : `mailsByKeys$` partagé par « Pour moi » et les envois revenus ; aucun autre cleanup.
- **dtos-mss** : hors passe (porteur de contrat).

### contract_impact

`python Tools/contracts/contract_impact.py check` : 
- `api-mcp` : aucun impact ;
- `client-mobile` : aucun impact (avertissement de lecture tolérante préexistant) ;
- `client-angular` : **IMPACT** — `AuditActionType` modifiée (actes 77-79), décodée par rang : **adapté** dans
  `audit.model.ts` (valeurs et libellés) et sa spec, sur l'arbre non commité (code-only).

### client-angular — fichiers à commiter sur TFS (code-only, `feature/nova-mss-weda-integration`)

| Fichier | Raison |
|---|---|
| `libs/mss/src/core/models/mail-follow-up.model.ts` (nouveau) | contrat `MailFollowUpDto`, motifs de clôture |
| `libs/mss/src/core/models/mail.model.ts` | `followUpDueAt` à l'envoi, `followUp` sur le message |
| `libs/mss/src/core/models/draft.model.ts` | le rappel suit le brouillon |
| `libs/mss/src/core/models/audit.model.ts` (+ spec) | actes 77-79 et leurs libellés |
| `libs/mss/src/core/services/mss-api.service.ts` | poser, clore, lister les rappels revenus |
| `libs/mss/src/core/utils/follow-up.util.ts` (+ spec, nouveaux) | échéance, textes du bandeau, objet « Relance : » |
| `libs/mss/src/features/mail/components/follow-up-picker/*` (nouveaux) | « Me rappeler si pas de réponse sous… » |
| `libs/mss/src/features/mail/components/follow-up-banner/*` (nouveaux) | bandeau, Relancer, Clore, « Me rappeler » |
| `libs/mss/src/features/mail/components/mail-compose/*` (+ `mail-compose-follow-up.component.spec.ts`) | choix à la rédaction, envoi, brouillon, relance |
| `libs/mss/src/features/mail/components/mail-detail/*` (+ `mail-detail.follow-up.spec.ts`) | bandeau et « Relancer » |
| `libs/mss/src/features/mail/components/mail-header/*` (+ `mail-header.follow-up.spec.ts`, nouveau) | marque « Sans réponse » ; un envoi revenu n'est pas un squelette |
| `libs/mss/src/features/mail/components/mail-list/mail-list.component.ts` (+ `.spec.ts`) | fusion de l'enrichissement par (dossier, UID) |
| `libs/mss/src/features/mail/mss-mail.component.ts` | fusion du rafraîchissement par (dossier, UID) |
| `libs/mss/src/features/mail/components/mail-list/mail-list.tag-view.spec.ts` | double d'API complété |
| `libs/mss/src/features/mail/services/mail-event.service.ts` | délai reproposé par « Relancer » |
| `libs/mss/src/features/mail/services/mail-state.service.ts` (+ `.handling.spec.ts`) | envois revenus en tête, rappel clos, restauration par (dossier, UID) |
| `e2e/mss-e2e/specs/functional.e2e.ts`, `support/e2e-backend.ts`, `support/session.ts` | E2E-FOLLOWUP-001 |

### Hors périmètre / restes

- **Stitch** (`/stitch-design`) : non appelé — aucun écran mobile nouveau ; le sélecteur et le bandeau s'insèrent
  dans la rédaction et le détail existants, au gabarit du bandeau « répondu » (task-459).
- **Flaky connu** : `MailboxSwitcherComponent` (`onAriaChanged`, `page-ionic-non-demontee`), rouge au 1er passage de
  la suite mobile, vert au 2e (1702/1702) — 7ᵉ occurrence consignée, la task de stabilisation est due.
- **Banc weda2** : premier montage `--serve-only` en panne d'outillage (« nx serve pas prêt après 480 s » ; la
  réoptimisation des dépendances Vite, concurrente du montage du backend). `nx serve` seul compile et sert ; rejoué
  une fois.

### Prévention (règle d'or)

- `conventions/csharp.md` S125 (« … ; … » en commentaire) : occurrence 31 (×4, attrapés par le contrôle mécanique
  avant le commit).
- `conventions/angular.md` `page-ionic-non-demontee` : occurrence 7.
- `conventions/angular.md` **`liste-multi-dossiers-cle-dossier-uid`** (nouvelle) : toute fusion, clé de suivi ou
  dédoublonnage de messages se fait par (dossier, UID) ; une ligne venue d'un autre dossier ne dépend pas d'un état
  calculé pour le dossier de la liste. Specs W13, W14 vus rouges.
- Les trous attrapés par l'e2e (règle 1b côté client : le parcours est le test d'intégration) étaient invisibles aux
  tests de composant ; ils sont désormais tenus par des tests unitaires vus rouges (M13, W13, W14).
- Le trou attrapé par l'e2e mobile (page hôte qui n'adopte pas l'état posé par un composant enfant) est fermé par un
  test de page (M13) ; il venait d'un écart d'architecture propre au mobile (le détail est un `@Input` de la page),
  que le test de composant ne pouvait pas voir.

### Reprise 1 après /review (revue anticipée, passage 1)

Périmètre : la liste « À corriger par la reprise » du passage 1. Les arbitrages AH1-AH3 ne sont pas touchés.

| Constat | Correctif | Test | Preuve rouge |
|---|---|---|---|
| **B1** fausse relance : garde sur le plus grand UID ingéré | chaque UID de la Boîte de réception arrivé depuis l'envoi doit être en base : plancher = plus grand UID ingéré arrivé avant le plus ancien envoi (date de la copie, à défaut de la demande, reculée d'un jour : la date d'en-tête est en heure du serveur), puis `UidsAwaitingIngestion` / `IsInboxIngested` par ensembles | intégration `AReplyBuriedUnderNewerMessages_NotYetIngested_NoFalseNudge` (réponse UID n, trois messages plus récents ingérés seuls) ; unitaires de la règle et du service | R1 (plus récent seul), R1b (jamais exigé) |
| B1, second volet (cache Redis 5 min) | non applicable : `ImapService.GetFolderAsync` revalide par STATUS, statut en cache 10 s (`CacheDurations.FolderStatus`) | — | — |
| **B2** échec de remise jamais classé hors vue conversation | lecture des accusés non classés extraite en `DeliveryReportReader` (partagée avec la vue conversation, comportement inchangé), jouée par l'évaluation en ligne, bornée à 20, **seulement quand un rappel est échu** (chemin de la liste des dossiers) | intégration `ADeliveryFailure_SeenOnlyFromTheInbox_ClosesTheFollowUp_AsASystemAct` (aucune ouverture de conversation) ; unitaires : lecture si échu, rien hors ligne, rien avant l'échéance | R2 (lecture retirée), R10 (lecture avant l'échéance) |
| **B3** relance qui clôt l'original | — (comportement existant) | `ANudge_ClosesTheOriginalFollowUp_InThePersonsName_AndCarriesItsOwn` (motif « relancé », imputé au titulaire, la relance porte son rappel à 7 j) | R3 |
| **B3** rappel porté par un brouillon | — | `AFollowUpChosenInADraft_IsReadBack_AndSetWhenTheDraftIsSent` (POST, GET, envoi du brouillon) | R5 |
| **B3** confirmation tardive d'un envoi mis de côté | — | `APendingSendConfirmedAfterItsDueDate_LeavesWithoutFollowUp` (hors ligne → 202, horloge +2 j, confirmation → 200, sans rappel) | R6 (400 sans le retrait de l'échéance) |
| **B3** « Clore » sans rappel | — | `ClosingWithoutFollowUp_Is404_InProblemDetails` | R7 |
| B3, 409 sans Message-ID | non atteignable par la route : un envoi de la plateforme porte toujours un Message-ID ; couvert par l'unitaire du service | — | — |
| **P1** coût sur chaque chargement | balayage `References LIKE` limité aux messages sans `In-Reply-To` (comme task-459) ; une évaluation par boîte réutilisée 10 s (horodatage Redis, horloge du service) : la liste des dossiers et `follow-ups/returned` d'un même chargement n'évaluent qu'une fois | unitaires : évaluation récente réutilisée, ancienne rejouée et horodatée ; `References` seul toujours prouvé par `AReplyBeforeTheDueDate…` | — (performance) |
| **P2** retour tracé deux fois | `MarkReturnedAsync` : mise à jour conditionnelle par rappel, seul celui qui marque trace | `ConcurrentEvaluations_TraceTheReturnOnlyOnce` (6 évaluations concurrentes) | R8 (lecture puis écriture) |
| **P3** annule et remplace | prémisse corrigée : le rappel de l'original était bien clos (In-Reply-To posé par l'annule-et-remplace), mais au motif « relancé ». Motif « clos » quand `CancelAndReplaceUid` est posé | `ACancelAndReplace_ClosesTheOriginalFollowUp_NotAsANudge` ; unitaire | R4 |
| **Défaut trouvé par l'autocontrôle** : plancher `Kind=Utc` comparé à des colonnes sans fuseau → 500 (Npgsql), un passage sur deux | plancher posé `DateTimeKind.Unspecified` | `AnEvaluationBeforeTheSentCopyIsIngested_DoesNotFail` (déterministe) | R9 (6 tests rouges) |
| **M1** liste mobile par UID seul | `track rowKey(mail)` et `isSelected(mail)` par (dossier, UID) (`isSameMail` exporté) | spec `mail-list` : Envoyés/42 et Boîte de réception/42, une seule ligne surlignée | M15 |
| **M2 / A1** ligne « Sans réponse » après relance | `refreshReply` (mobile `MailActionsService`, weda2 `MailStateService`) pose le rappel relu (`applyFollowUp`) | specs mobile `mail-actions` et weda2 `mail-state` : la ligne quitte « À traiter » | M14, W15 |
| **M3** testid prolongeant `mail-row-` | `followup-chip-{uid}` dans les deux clients, leurs specs et leurs parcours | — | — |
| **M4 / A3** assertion e2e qui ne pouvait pas rougir | les deux parcours affirment, après « Clore » et avant les relectures serveur, que la **ligne** (par son objet) a quitté « À traiter » (mobile : retour à la liste) | E2E-FOLLOWUP-001 | voir ci-dessous |
| **A2** total gonflé | `toHandlePage$` garde le total du dossier | spec `mail-state.handling` (total 2, plus 3) | W16 |

**Mutations api-mail** (`mutate_462_r1.py`, build + classe `FollowUpEndToEndTests`, restauration octet pour octet puis
date) : R1-R9 toutes rouges sur leur test visé ; « restauré : 14/14 verts ». R10 (unitaire) rouge, restauré.
Pendant la première série, `…SurvivesAMoveOutsideThePlatform…` rougissait sous des mutations sans rapport : ce n'était
pas un flaky mais le défaut `Kind=Utc` ci-dessus (rejoué seul : 2 rouges sur 4, erreur Npgsql lue), corrigé, puis 4/4
verts et la série rejouée propre.

**Mutations clients** : mobile M14, M15 rouges ; weda2 W15, W16 rouges (Vitest par PowerShell, rouges sur assertion).

**E2E-FOLLOWUP-001, nouvelles assertions** (banc weda2 `--serve-only`, qui sert aussi l'app mobile ; rappel réarmé par
l'API entre deux passages, échéance à +2 s comme le seed) :
- mutations posées : serveur (`GetReturnedKeysAsync` garde les rappels clos), weda2 (`applyFollowUp` ne retire pas la
  ligne), mobile (`applyFollowUp` ne retire pas la ligne) ; marqueurs prouvés servis dans les chunks ;
- mobile : avec la seule mutation serveur, rouge sur la relecture serveur mais la ligne avait quitté la liste (l'état
  client la retire, le retour ne recharge pas « À traiter ») ; avec la mutation client en plus, **rouge sur « le message
  quitte « À traiter » »** ;
- weda2 : **rouge sur « le message quitte « À traiter » »** ;
- banc propre remonté (marqueurs prouvés absents) : mobile **1 passed**, weda2 **1 passed**.

**Builds / tests de la reprise**

| Repo | Build | Tests |
|---|---|---|
| api-mail | vert | suite complète 8 296 tests, 0 échec, sur `1a656785` ; marqueur vert `1a656785` |
| client-mobile | `npm run build` vert | Karma 1705/1705 ; marqueur vert `82fc95e` |
| client-angular | `nx build weda2` vert | mss-lib 1 923/1 923, `nx test weda2` vert, ESLint 0 erreur, Prettier propre sur mes blocs ; marqueur vert sur l'arbre final |

**Commits** : api-mail `80ba1762`, `1a656785` ; client-mobile `82fc95e` ; client-angular non commité (code-only).

**contract_impact** (rejoué) : api-mcp aucun impact ; client-mobile aucun impact ; client-angular IMPACT
`AuditActionType` — adapté (inchangé depuis le passage 1).

**client-angular — fichiers ajoutés ou modifiés par la reprise** (à commiter sur TFS avec ceux du Develop log) :

| Fichier | Raison |
|---|---|
| `libs/mss/src/features/mail/services/mail-state.service.ts` | relecture après relance qui pose le rappel ; pagination non gonflée |
| `libs/mss/src/features/mail/services/mail-state.service.spec.ts` | relecture après relance (A1) |
| `libs/mss/src/features/mail/services/mail-state.service.handling.spec.ts` | total de la page 1 (A2) |
| `libs/mss/src/features/mail/components/mail-header/mail-header.component.html` (+ `mail-header.follow-up.spec.ts`) | testid `followup-chip-{uid}` (M3) |
| `e2e/mss-e2e/specs/functional.e2e.ts` | testid renommé ; sortie de la ligne affirmée (A3) |

**Autocontrôle du correctif** (« ce que ça casse ailleurs ») : `refreshReply` sert aussi « Voir la réponse » et la
relecture après une réponse ordinaire ; un message reçu n'a pas de rappel (no-op), et seul un rappel revenu figure dans
« À traiter » : pas d'effet de bord. La lecture des accusés extraite garde le comportement de la vue conversation
(`ConversationServiceTests` verts sans changement). Le défaut `Kind=Utc` et le coût IMAP sur la liste des dossiers ont
été trouvés et corrigés dans cette même reprise.

**Flaky connu** : `ImapServiceTests.GetFolderNotSeenAsync_HappyPath_TagsTheImapActivityWithPerCommandDurationsAsync`
(ActivityListener global) rouge une fois en suite complète, vert au rejeu du projet (4 377/4 377).

**Prévention (règle d'or)** :
- `conventions/csharp.md` : nouvelle consigne `npgsql-instant-utc-colonne-sans-fuseau` ; S125 occurrence 32 ;
  `premisse-de-test-integration` occurrence 3 (le test unitaire de l'échec de remise simulait sa prémisse) ;
- `conventions/angular.md` `liste-multi-dossiers-cle-dossier-uid` : occurrence 2 (un défaut trouvé dans un client se
  cherche aussitôt dans l'autre) ;
- `conventions/e2e.md` : nouvelle consigne `disparition-lue-sur-une-marque-derivee`.

### Reprise 2 après /review (revue anticipée, passage 2)

Périmètre : api-mail seul (mobile et weda2 approuvés au passage 2). Les arbitrages AH1-AH3 ne sont pas touchés.

| Constat | Correctif | Test | Preuve rouge |
|---|---|---|---|
| **F3** (récidive B1) plancher fondé sur des dates, trompable | le plancher est l'`UIDNEXT` de la Boîte de réception relevé **à la demande** (envoi ou détail), avec son `UIDVALIDITY` (`MailFollowUp.InboxUidNext`, `InboxUidValidity`, migration `20261121090000`) ; `MailFollowUpRule.FloorOf` : plus petit `UIDNEXT` des rappels échus moins un ; un relevé absent ou un `UIDVALIDITY` changé → pas de plancher (toute la boîte attendue) | intégration `AnOldMessagePutBackAboveAnUningestedReply_NoFalseNudge` (ancien message remis avec sa date d'origine, UID au-dessus de la réponse, seul ingéré) ; unitaires `FloorOf`, `UIDVALIDITY` changé, relevé à l'envoi | **rouge sur le code d'avant la reprise 2** (plancher par dates) |
| **F2** (récidive B1) plancher non prouvé | — (le plancher par UIDNEXT le rend déterministe) | intégration `AnOldInboxMessageNeverIngested_DoesNotHoldTheReturn` (historique jamais ingéré, le rappel revient) | rouge sur le code d'avant ; R11 (aucun plancher) |
| **F1** (récidive B2) échec noyé sous plus de 20 accusés | avant un retour, les accusés non classés de la Boîte de réception **au-dessus du plancher** sont lus du plus ancien au plus récent (`GetUnclassifiedInboxReportsAsync`, `DeliveryReportReader.ReadAsync`), par paquets de 20 ; s'il en reste, ou si la lecture s'interrompt, le retour attend | intégration `ADeliveryFailureFollowedByManyReports_StillClosesTheFollowUp` (échec daté avant 21 accusés plus récents) ; unitaires : lecture au-dessus du plancher avant la recherche des échecs, retour différé (trop d'accusés, lecture interrompue) | rouge sur le code d'avant (après avoir daté les accusés du test : sans en-tête `Date`, l'ordre « plus récents d'abord » ne les ordonnait pas) |
| **F4** accusé dans un dossier disparu bloquant la lecture | `MailExportService.BuildEmlAsync` : `FolderNotFoundException` → `NotFound` (le lecteur le classe « inconnu » et passe au suivant ; l'export d'un message d'un dossier supprimé répond 404) | unitaire `BuildEmlAsync_FolderGone_ReturnsNotFound` | mutation (garde neutralisée) rouge |
| **F5** clé de cache non normalisée | `RedisKeys.FollowUp.Evaluated` normalise l'adresse ; sans adresse, ni lecture ni écriture du cache | unitaire `…TheEvaluationStamp_NamesTheMailboxNormalised_AndNeedsOne` | mutation (normalisation retirée) rouge |
| **F7** 409 sans Message-ID non prouvé | — (comportement existant) | intégration `AFollowUpOnASentMessageWithoutMessageId_Is409` (copie d'Envoyés déposée sans Message-ID) | R12 (409 → 200) |

**Migration (règle 7c)** : `20261121090000_AddMailFollowUpInboxFloor` lue : deux colonnes nullables ajoutées à
`MailFollowUps`, aucune donnée existante modifiée ni supprimée ; descente : les deux colonnes retirées. Mapping EF aligné
(`HasColumnName` sur les constantes de la migration) ; la suite complète bâtit le schéma depuis le modèle et joue les
migrations.

**Limite assumée (liée à AH1)** : pour un rappel posé depuis le détail, le plancher est l'`UIDNEXT` de la demande : une
réponse (ou un échec de remise) arrivée entre l'envoi et la demande et pas encore ingérée n'est pas attendue. Si
l'arbitrage AH1 retient « seules les réponses postérieures à la demande comptent », c'est exactement la règle.

**Autocontrôle du correctif** : la relecture de la Boîte de réception a lieu désormais aussi à chaque demande (STATUS,
cache 10 s) ; une panne y laisse le plancher vide sans faire échouer la demande (best-effort, toute la boîte attendue).
Un rappel antérieur à la migration n'a pas de plancher : son retour ne peut qu'être retardé. Le lecteur partagé garde
le comportement de la vue conversation (`ReadUnreadAsync` délègue à `ReadAsync`).

**Mutations** : R11, R12 (intégration) rouges, « restauré : 18/18 » ; F4, F5 (unitaires) rouges, restaurés (42/42).

**Builds / tests** : api-mail suite complète 8 308 tests, 0 échec, sur `dc39d1d3` ; marqueur vert `dc39d1d3`. Mobile et weda2 inchangés depuis le passage 2
(marqueurs verts `82fc95e` et arbre weda2).

**Commit** : api-mail `dc39d1d3`.

**Prévention (règle d'or)** : `conventions/csharp.md`, deux consignes neuves : `repere-imap-par-uidnext` (un repère
« depuis tel instant » dans un dossier IMAP se prend en UID, pas en date) et `lot-borne-avant-decision` (un traitement
par lots qui conditionne une décision lit depuis un repère, dans l'ordre d'arrivée, et diffère la décision s'il en reste) ;
S125 occurrence 33.

### Reprise 3 après /review (passage 3, arbitrages rendus le 2026-11-20)

Périmètre : api-mail (R1, R2 + AH1, R3, AH2, AH3). Mobile et weda2 inchangés (approuvés au passage 2).

| Constat | Correctif | Test | Preuve rouge |
|---|---|---|---|
| **R1** UIDVALIDITY perdu sur le chemin du cache | cause plus large : le chemin frais lui-même (`ImapService.BuildFolderDto`, STATUS sans `UidValidity`) rendait 0, la garde `UIDVALIDITY` n'était jamais active. Le STATUS demande l'`UIDVALIDITY` (même aller-retour), `BuildFolderDto` le pose, `FolderStatusCache` le transporte, `CreateCachedFolderDto` le rend ; un `UIDVALIDITY` inconnu (0, entrée de cache antérieure) ne contredit plus le plancher | intégration `OnACacheHitOfTheInbox_TheFloorHolds` (demande lue sur le serveur, évaluation servie par le cache, historique non ingéré) ; unitaires `CreateCachedFolderDto_CarriesTheUidValidity`, `FloorOf_AnUnknownUidValidity_ContradictsNothing` | R13 (cache sans UIDVALIDITY + comparaison stricte) |
| **R2 + AH1** repère et fenêtre | `CaptureAnchorAsync` relève le repère (instant, UIDNEXT, UIDVALIDITY) **avant** l'envoi SMTP, transmis à `RecordSentAsync` par `OutgoingMailService` (envoi direct, brouillon, confirmation, annule et remplace) ; `RequestedAt` = instant du repère ; réponses et échecs ne comptent qu'à partir de la demande, moins 5 min de tolérance d'horloge (INTERNALDATE à la seconde, horloge du serveur de messagerie — un VM Docker du banc retarde d'≈ 1 s) | intégration `AReplyBeforeTheRequestFromTheDetail_DoesNotCloseIt` ; unitaires : ordre repère → SMTP → rappel (`SendAsync_CapturesTheFollowUpAnchorBeforeTheSmtpSend…`), repère utilisé tel quel, fenêtre depuis la demande | AH1 rouge sur le code d'avant et par mutation |
| **R3** retour différé non prouvé | — | intégration `ManyReportsBeforeTheFailure_TheReturnWaits_ThenTheFailureClosesIt` (20 accusés avant l'échec : première évaluation ni retour ni clôture, la suivante clôt « non distribué ») | R14 (`return allRead;`) |
| **AH2** réponse automatique, tiers | réponses : `!IsAutomatic`, et expéditeur parmi les destinataires À/Cc de l'envoi (`MailFollowUp.RecipientAddresses`, migration `20261121120000`) ; destinataires inconnus (rappel antérieur) : tout expéditeur | intégration `AnOutOfOfficeAutoReply_DoesNotCloseIt`, `AMessageFromAThirdParty_DoesNotCloseIt` ; unitaire `ClosesTheFollowUp_…` | rouges sur le code d'avant et par mutation (AH2a, AH2b) |
| **AH3** échec partiel | un échec ne clôt que si tous les destinataires sont en échec : adresses `Final-Recipient` des groupes `failed` relues dans les rapports (`DeliveryReportParser.FailedRecipients`, `DeliveryReportReader.ReadFailedRecipientsAsync`) ; rapport illisible : ni clôture ni retour cette fois | intégration `ADeliveryFailureOfOneRecipientOutOfTwo_KeepsItOpen`, `ADeliveryFailureOfAllRecipients_ClosesIt` ; unitaires du service, de la règle et du parseur | rouge sur le code d'avant (échec partiel) et par mutation |

**Migration (règle 7c)** : `20261121120000_AddMailFollowUpRecipients` lue : une colonne `text` nullable, aucune
donnée existante modifiée ni supprimée, descente qui la retire, mapping EF aligné sur la constante.

**Limites assumées** : la preuve de l'ordre « repère avant SMTP » est unitaire (le banc ne sait pas faire arriver un
rebond pendant l'envoi SMTP) ; le filtre de date des échecs de remise (AH1) n'a pas de test d'intégration dédié — un
échec antérieur à la demande est de toute façon sous le plancher et jamais classé par l'évaluation.

**Mutations** : `mutate_462_r3.py` — R13, R14, AH1, AH2a, AH2b, AH3 toutes rouges sur leur test visé, « restauré :
25/25 ». Rouges sur le code d'avant la reprise 3 : AH1, AH2a, AH2b, AH3 (échec partiel).

**Autocontrôle du correctif** : le STATUS du chemin de liste porte un item de plus (même aller-retour) ; le corps
`FolderDto` de `GET folders/{dossier}` porte désormais un `uidValidity` non nul, déjà déclaré au contrat. La tolérance
de 5 min ne compte comme postérieure qu'une réponse arrivée dans les 5 min qui précèdent la demande.

**Builds / tests** : api-mail suite complète verte (domain 385, infrastructure 749, application 4 393, api 1 388, intégration 1 396 + 16 ignorés, 0 échec, aucun FATAL). Mobile et weda2 inchangés.

**Commit** : api-mail `a3923a85`.

**Prévention (règle d'or)** : `conventions/csharp.md`, deux consignes neuves : `champ-de-dto-tous-les-chemins` (un champ
dont dépend une décision se vérifie sur tous les chemins qui fabriquent le DTO, frais et cache) et
`fenetre-imap-tolerance-horloge` ; S125 occurrence 34.

### Reprise 4 après /review (revue anticipée, passage 4)

Périmètre : api-mail (N1, N2). Mobile et weda2 inchangés.

| Constat | Correctif | Test d'intégration | Preuve rouge |
|---|---|---|---|
| **N1** la liste des messages relisait le rapport d'échec sur le serveur | Les adresses en échec (`Final-Recipient` et `Original-Recipient` des groupes `failed`) sont lues **au classement** du rapport, qui relit déjà le message (`DeliveryReportReader.ReadAsync`, partagé par l'évaluation et la vue conversation). Elles sont gardées dans `Mails.ReportFailedRecipients` (migration `20261121150000`). `FindDeliveryFailuresAsync` les rend, et AH3 se décide en base. `IDeliveryReportReader.ReadFailedRecipientsAsync` est retiré, ainsi que l'état « indécis ». `ApplyAsync` et l'évaluation ne vont plus sur le serveur pour un rappel. | `AFailureClassifiedThenGoneFromTheServer_TheListStillClosesIt` : rapport classé par la vue conversation puis effacé du serveur (EXPUNGE). La liste d'Envoyés répond 200 et clôt le rappel « non distribué ». | Rouge sur le code de la reprise 3 (le rapport disparu ne donnait aucune adresse, le rappel restait ouvert). Mutation N1 (adresses non gardées au classement) : 6 tests rouges, dont celui-ci. |
| **N2 (récidive)** rebond rapide, et échec antérieur à la demande | Comportements déjà dans le code de la reprise 3 : seules leurs preuves d'intégration manquaient. | `ARapidBounceDuringTheSmtpSend_ClosesIt` : le SMTP réel, puis un rapport d'échec déposé dans la Boîte de réception avant que l'envoi ne rende la main (décorateur `BouncingSmtp` sur `ISmtpService`, fournisseur externe). `AFailureClassifiedBeforeTheRequestFromTheDetail_DoesNotCloseIt` : échec arrivé une heure avant et classé par la vue conversation, puis rappel posé depuis le détail. Le rappel reste ouvert et revient. | Mutations N2a (repère relevé après le SMTP) et N2b (filtre de date des échecs retiré) : chacune rouge sur son test seul. Vertes sur le code de la reprise 3, qui portait déjà ces comportements. |

**Suggestions du passage 4 reprises** : `Original-Recipient` rapproché des À/Cc (test unitaire
`FailedRecipients_AlsoTheOriginalRecipient_OfAFailedGroup`). Un rapport illisible ne bloque plus le retour, puisque l'état
« indécis » a disparu avec la relecture.

**Tests unitaires** :
- `Get_ADeliveryFailure_IsClassifiedWithItsFailedRecipients` (vue conversation) ;
- `ApplyAsync_ADeliveryFailureOfAllRecipients_IsDecidedInTheDatabase_WithoutTheMailServer` (aucun appel au lecteur
  d'accusés ni à IMAP) ;
- `GetReturnedAsync_TwoReportsEachFailingOneRecipient_CloseTheFollowUp` ;
- signatures `SetReportAsync` mises à jour.

**Migration (règle 7c)** : `20261121150000_AddMailReportFailedRecipients` lue. Elle ajoute une colonne `text` nullable sur
`Mails`, sans défaut. Aucune donnée n'est modifiée ni supprimée, et la descente retire la colonne. Le mapping EF passe par
la constante (FluentMigrator, sans instantané de modèle).
- Les rapports classés avant gardent `NULL`, soit aucune adresse : un rappel dont les destinataires sont connus n'est pas
  clos par eux.
- Ils précèdent de toute façon toute demande de rappel, qui n'existe qu'avec cette task.

**Autocontrôle du correctif** :
- `SetReportAsync` n'a qu'un appelant (le lecteur d'accusés), mis à jour.
- La vue conversation (`GetReportsAsync`) n'est pas touchée.
- `CloseAnsweredAsync` ne fait plus aucun appel IMAP, et ses deux appelants (`ApplyAsync`, l'évaluation) lisent la base.
- La réingestion d'un rapport ne remet pas son classement à zéro.

**Mutations** : `mutate_462_r4.py` : N1, N2a et N2b rouges, « restauré : 28/28 ».

**Builds / tests** : api-mail suite complète verte (domain 385, infrastructure 749, application 4 396, api 1 388, intégration 1 399 + 16 ignorés, 0 échec, aucun FATAL). Commit `be75a84f`.

**Prévention (règle d'or)** :
- `conventions/csharp.md` : `decision-de-liste-en-base` (ce que décide la liste se lit en base, et ce qu'il faut lire
  sur le serveur se lit une fois, au classement). S125, occurrence 35.
- `agents/develop.md`, mode reprise, point 3 : un test exigé par la revue n'est jamais déclassé en « limite assumée »
  sans décision humaine.

## Sonar log

Projet `healthplatform-api-mail` (SonarQube 9.9.8), branche `feat/task-462-sans-reponse-depuis-n-jours-relance`.
Deux analyses complètes : build Release, 5 suites avec couverture OpenCover, scan. Le serveur était arrêté, il a été
redémarré (`sonarqube_db` puis `sonarqube`).

| Itération | Constat new code | Correctif | Commit |
|---|---|---|---|
| 1 | 6 : S1905 ×4 (casts `(string?)` inutiles, `MailFollowUpRepository`, `MailFollowUpService`), S125 ×1 (commentaire de `MailRepository` venu du correctif « boîte de Virginie » fait sur `develop`), CA1861 ×1 (`SetEquals(new[] { … })` dans un `Arg.Is`) | refactor pur, aucun changement de comportement | api-mail `c4c5e976` |
| 2 | 0 issue, 0 hotspot | — | — |

- Phase 1 (new code) : Quality Gate OK, `new_coverage` = 95,7 % (seuil ≥ 95 %).
- Phase 2 (legacy) : sans objet, 0 code smell sur le projet.
- Suites jouées par l'analyse : domaine 385, application 4 396, infrastructure 749, api 1 388, intégration 1 399 (16
  ignorés), **0 échec**.
- Vert api-mail marqué par `/sonar` à `c4c5e976`.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 96,0 % | 95,7 % | −0,3 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 0 (6 à l'itération 1, corrigés) | 0 |
| Coverage (projet) | 97,6 % | 97,5 % | −0,1 pt |
| Duplication | 0,3 % | 0,3 % (new code 0,04 %) | → |
| Reliability / Security / Maintainability | A / A / A | A / A / A | → |

**Conventions** (`conventions/csharp.md`) :
- CA1861 : occurrence 10. Le contrôle mécanique de `agents/develop.md` §Q 2b ne cherchait que `SequenceEqual` : il est
  élargi à `SetEquals`.
- S125 : occurrence 36.
- S1905 : nouvelle entrée, avec son contrôle mécanique.

## Lint log

- Mode : A (chaîné), scope `tag:scope:mss` (défaut : `mss`, `mss-lib`, `mss-e2e`), base `origin/next`. Aucun override
  `**LintBase**` / `**LintProjects**`.
- Arbre : branche `feature/nova-mss-weda-integration` (code seul, rien de commité). `git status` identique avant et après
  l'étape (31 entrées de la task).
- Comptage : `npx eslint libs/mss apps/mss e2e/mss-e2e --format json` (même contournement que task-367 et task-487).
  Attribution à la task par `git diff -U0 HEAD` et les fichiers non suivis.
- Baseline : **0 error** / 100 warnings (75 `jsdoc/require-example`, 22 `max-lines`, 3 `complexity`), le même compte
  qu'à task-487.
- Constats sur une ligne ajoutée par la task : **0**.
  - Les `max-lines` et le `complexity` des fichiers touchés existaient avant la task. Ces fichiers ont grossi, sans
    nouvel avertissement.
  - Cela vaut pour `mail-header` (906 lignes), `mail-list`, `mss-mail`, `mail-state.service`, `mss-api.service`, la
    composition, le détail et les specs e2e.
- Final : 0 error / 100 warnings. Itérations : 0 / 5 (rien à corriger, aucun fichier modifié).
- Build / tests : non rejoués. Arbre inchangé, le vert de `/develop` reste valide (`green.py check` : `f8164238`).

## Code Review Summary

### Passage 1 (revue anticipée) — CHANGES REQUESTED

Revue de code par un relecteur indépendant (sous-agent, code seul, sans le Develop log), constats lourds vérifiés sur
le code. Revus : api-mail `f8678551`, dtos-mss `d668837`, client-mobile `fc0a981`, client-angular (arbre non commité).

**4a — règle 1b** (comportement → test d'intégration → preuve rouge) :

| Comportement | Test d'intégration | Preuve rouge |
|---|---|---|
| envoi avec rappel → retour après l'échéance, demandeur (délégataire) lu par le titulaire, acte système, compteur « À traiter », « Clore » imputé | `ASentMessageWithoutReply_ReturnsAfterItsDueDate_WithTheRequester_ThenCloseRemovesIt` | M1, M4, M5, M6, M10, M11, M12 |
| réponse par `References` seul avant l'échéance, pas de retour tant qu'elle n'est pas ingérée | `AReplyBeforeTheDueDate_ClosesTheFollowUp_AndNoFalseNudgeWhileItIsNotSynchronised` | M2, M3 |
| échéance passée → 400 `ProblemDetails` (détail et envoi) | `APastDueDate_Is400_InProblemDetails_FromTheDetail_AndAtSending` | M7 |
| rappel sur un message reçu → 400 | `AFollowUpOnAReceivedMessage_Is400` | M8 |
| rappel posé depuis le détail, survit au déplacement | `AFollowUpRequestedFromTheDetail_SurvivesAMoveOutsideThePlatform_AndReturnsOnTheMovedCopy` | M9 |
| **la relance clôt le rappel précédent (« relancé », imputé)** | **aucun** (unitaire seul) | — |
| **clôture sur échec de remise** | **aucun** (unitaire qui simule sa propre prémisse) | — |
| **le rappel suit le brouillon (envoi depuis le brouillon)** | **aucun** | — |
| **confirmation tardive d'un envoi mis de côté : échéance passée retirée** | **aucun** (unitaire seul) | — |
| **« Clore » sans rappel → 404, sans Message-ID → 409** | **aucun** | — |

**4b — clause DoD** : E2E-FOLLOWUP-001 v1 au catalogue (diff api-mail), déclaré v1 par les deux clients. Le `## E2E log`
sera contrôlé par la validation finale.

**4c — contract_impact** :
- `api-mcp` : aucun impact ;
- `client-mobile` : aucun impact ;
- `client-angular` : IMPACT — `AuditActionType` décodée par rang : **adapté** (`audit.model.ts`, actes 77-79 et
  libellés, spec), arbre non commité.

**Verdicts par repo** : api-mail ❌ · dtos-mss ✅ · client-mobile ❌ · client-angular ❌.

#### À corriger par la reprise

- **B1 — api-mail, « pas de fausse relance » fondée sur le plus grand UID ingéré.** `MailFollowUpRule.IsInboxIngested`
  et `MailFollowUpRepository.GetInboxMaxIngestedUidAsync` : la page d'en-têtes n'écrit que les UID affichés. Une
  réponse (UID 500) suivie de 60 messages (501-560) : la page 1 ingère 511-560, max ingéré = max serveur, la réponse
  n'est pas en base → **fausse relance**. Comparer des ensembles (tout UID serveur de la Boîte de réception présent en
  base pour la génération courante), sans se fier à une liste d'UID servie par le cache Redis de 5 min. Test
  d'intégration : réponse noyée sous des messages plus récents, page 1 seule chargée → aucun retour ; vu rouge.
- **B2 — api-mail, la clôture sur échec de remise ne se déclenche presque jamais.** `FindDeliveryFailuresAsync` lit
  `ReportKind == Failed`, que seul `ConversationRepository` (vue conversation) renseigne. Un médecin qui ne travaille
  que dans la boîte : le rapport reste non classé, le rappel revient « Sans réponse ». Classer les rapports nécessaires
  avant l'évaluation (ou lire l'échec autrement), et un test d'intégration : rapport d'échec déposé, aucune ouverture
  de conversation → rappel clos (acte système), pas de retour ; vu rouge. Le test unitaire actuel simule sa prémisse.
- **B3 — api-mail, règle 1b** : tests d'intégration de bout en bout, vus rouges, pour la relance qui clôt le rappel
  précédent (motif « relancé », imputé à la personne, via l'envoi avec `InReplyTo`), le rappel porté par un brouillon
  envoyé, la confirmation tardive d'un envoi mis de côté (échéance passée retirée), et « Clore » sans rappel (404
  `ProblemDetails`) ; sans Message-ID (409) si le cas est atteignable.
- **P1 — api-mail, performance** (chemin chaud) : l'évaluation tourne deux fois par chargement de la page 1 (compteurs
  des dossiers et `follow-ups/returned`) et, dès qu'un rappel est ouvert, balaie `References LIKE '%id%'` sur tous les
  messages reçus, sans index. Restreindre le balayage `References` aux messages sans `InReplyTo` (comme task-459), et
  ne pas réévaluer deux fois pour un même chargement. Plan (EXPLAIN) consigné dans le Develop log.
- **P2 — api-mail, retour tracé deux fois** : `MarkReturnedAsync` lit puis met à jour sans garde ; deux évaluations
  concurrentes tracent deux `FollowUpReturned`. Mise à jour conditionnelle (seules les lignes encore non revenues),
  test vu rouge.
- **P3 — api-mail, annule et remplace** (task-376) : l'original annulé garde son rappel ouvert et revient plus tard
  « Sans réponse » sur un message annulé. Clore le rappel de l'original annulé, au nom de la personne qui envoie le
  remplaçant ; test d'intégration vu rouge.
- **M1 — client-mobile, identité (dossier, UID)** : `mail-list.component.html` suit les lignes par `mail.uid` et la
  sélection par `mail.uid === selectedUid()`. Envoyés/42 et Boîte de réception/42 dans « À traiter » : même clé, la
  mauvaise ligne surlignée. Clé (dossier, UID) partout (convention `liste-multi-dossiers-cle-dossier-uid`) ; spec vue
  rouge.
- **M2 / A1 — mobile et weda2, après une relance la ligne d'origine reste « Sans réponse »** : la relecture après
  envoi (`refreshReply`) ne pose que `reply` / `isAnswered`, jamais le rappel clos (« relancé »). Adopter le `followUp`
  relu (`applyFollowUp`) dans la liste ; specs vues rouges, des deux côtés.
- **M3 — mobile et weda2, convention `testid-prefixe-d-un-autre`** : `mail-row-followup-{uid}` prolonge le préfixe de
  ligne `mail-row-` (sélecteurs `[data-testid^="mail-row-"]` du spec de liste et du parcours mobile). Renommer (par
  ex. `followup-chip-{uid}`) dans les deux clients et les deux parcours.
- **M4 / A3 — E2E-FOLLOWUP-001, assertion qui ne peut pas rougir** : « le message quitte « À traiter » » n'est vérifié
  que par la disparition du bandeau (mobile) ou de la marque (weda2), qui disparaît dès que `isReturned` tombe.
  Affirmer que la **ligne** (par son objet) a quitté la liste, dans les deux clients ; vu rouge.
- **A2 — weda2, total gonflé** : `toHandlePage$` rend `total: rest.total + returned.length`, d'où un « charger plus »
  vide. Ne pas compter les envois revenus dans la pagination (comme le mobile).

#### Arbitrage humain

- **AH1 — rappel posé depuis le détail sur un message déjà répondu** : la réponse antérieure le clôt aussitôt
  (« réponse reçue le <date ancienne> »). Recommandation : ne compter que les réponses arrivées **après** la demande.
- **AH2 — réponse automatique d'absence** (`Auto-Submitted`, `Mails.IsAutomatic` de task-456) : elle clôt aujourd'hui
  le rappel, alors que c'est le cas où il sert le plus ; et un message d'un non-destinataire compte comme réponse.
  Recommandation : exclure les messages automatiques ; ne compter que les expéditeurs parmi les destinataires (À, Cc).
- **AH3 — échec de remise partiel** (un destinataire sur plusieurs) : il clôt le rappel pour tous. Recommandation : ne
  clore que si tous les destinataires sont en échec.

#### Suggestions (non bloquantes)

- Une réponse rangée dans la Corbeille, ou classée ailleurs par une règle serveur avant l'évaluation, n'est pas vue
  (fausse relance possible) : à mesurer avant de corriger.

### Passage 2 (revue anticipée, après reprise 1) — CHANGES REQUESTED

Relecteur indépendant, diff de la reprise lu d'abord (api-mail `f8678551..1a656785`, mobile `fc0a981..82fc95e`, arbre
weda2). Rien de cassé ailleurs par la reprise : `ConversationService` délégant au lecteur (comportement inchangé),
enregistrements DI, `refreshReply` (sans effet hors rappel), export d'`isSameMail`, fusions weda2 par `mailKeyString`,
pagination weda2 (A2), parcours e2e (présence vue avant l'absence), requêtes traduites en SQL, S1067.

**Statut des constats du passage 1** : B3, P1, P2, P3, M1, M2/A1, M3, M4/A3, A2 corrigés. **B1 et B2 partiels** (ci-dessous).

**Verdicts par repo** : api-mail ❌ · dtos-mss ✅ · client-mobile ✅ · client-angular ✅.

**4c — contract_impact** : inchangé (api-mcp, client-mobile : aucun impact ; client-angular : `AuditActionType`, adapté).

#### À corriger par la reprise

- **F1 (récidive de B2) — api-mail, l'échec de remise peut encore être manqué.** `GetUnreadReportsAsync` rend les 20
  accusés non classés les plus **récents** ; l'évaluation fait revenir le rappel dans la même passe. Un échec arrivé peu
  après l'envoi, suivi de plus de 20 accusés plus récents non classés (accusés d'autres envois, arriéré historique),
  n'est pas lu : le message non distribué revient « Sans réponse », et plus jamais relu ensuite (la lecture n'a lieu que
  pour un rappel échu et pas encore revenu). Correctif attendu : avant un retour, classer **tous** les accusés non
  classés arrivés depuis le plus ancien envoi échu (du plus ancien au plus récent, ou bornés par date), ou différer le
  retour tant qu'il en reste (même logique d'ensemble que B1). Test d'intégration : échec de remise suivi de plus de 20
  accusés plus récents non classés → aucun retour, rappel clos ; vu rouge.
  - **F4 (même correctif)** : un accusé non classé dont le dossier a disparu fait échouer `BuildEmlAsync` en `Error`
    (pas `NotFound`), et la lecture s'arrête sur lui à chaque évaluation : plus rien n'est classé. Le lecteur ne doit pas
    rester bloqué sur un accusé illisible (le classer « inconnu », ou le passer).
- **F2 (récidive de B1) — api-mail, le plancher n'est prouvé par aucun test d'intégration (règle 1b).** Toutes les
  boîtes de test ont une Boîte de réception entièrement ingérée ou vide : forcer « aucun plancher » (toute la boîte
  attendue) laisserait probablement tout vert, et désactiverait en production le rappel de toute boîte dont l'historique
  n'est pas ingéré. Test attendu : un message ancien, déposé avant l'envoi et jamais ingéré, et le rappel revient
  quand même après l'échéance ; vu rouge sans le plancher.
- **F3 (récidive de B1) — api-mail, plancher fondé sur des dates, trompable.** Le plancher est le plus grand UID ingéré
  dont `ArrivalDate ?? SentDate` précède l'envoi ; UID et date ne vont pas ensemble. Un ancien message remis dans la
  Boîte de réception (IMAP COPY/MOVE garde INTERNALDATE) reçoit un UID au-dessus d'une réponse non ingérée : une fois
  ingéré, le plancher saute la réponse → fausse relance. Même effet avec un en-tête `Date` antidaté et `ArrivalDate`
  nul. Piste déterministe : retenir l'`UIDNEXT` de la Boîte de réception au moment de l'envoi (ou de la demande) et en
  faire le plancher. Le choix d'implémentation est libre, tant que le plancher ne dépend plus des dates ; test vu rouge.
- **F5 — api-mail, convention `cle-de-cache-de-boite`** : `RedisKeys.FollowUp.Evaluated(userContextInfo.Email)` ne
  normalise pas l'adresse et met en cache même quand elle est vide. Appliquer la consigne.
- **F7 — api-mail, règle 1b** : le 409 (message envoyé sans Message-ID) est atteignable (copie d'Envoyés déposée sans
  Message-ID) et n'est pas prouvé. Test d'intégration vu rouge.

#### Arbitrage humain

Inchangé : AH1, AH2, AH3 du passage 1.

#### Suggestions (non bloquantes)

- F6 : la preuve de P2 (évaluations concurrentes) est probabiliste ; une preuve déterministe au niveau du dépôt serait
  plus solide.
- F8 : mobile `isSelected` reprend la tolérance d'`isSameMail` (dossier absent = égal) ; `threadChildren` reste suivi
  par `child.uid` (antérieur).

### Passage 3 (revue anticipée, après reprise 2) — CHANGES REQUESTED, chaîne arrêtée

Relecteur indépendant sur le diff de la reprise 2 (api-mail `1a656785..dc39d1d3`), R1 vérifié sur le code
(`ImapHelper.CreateCachedFolderDto` ne pose pas `UidValidity`, `FolderStatusCache` ne le porte pas).

**Statut des constats du passage 2** : F3, F4, F5, F7 corrigés. **F1 et F2 partiels.**

**Verdicts par repo** : api-mail ❌ · dtos-mss ✅ · client-mobile ✅ (passage 2) · client-angular ✅ (passage 2).

#### Bloquants

- **R1 (B1 → F2 → R1, troisième apparition) — le plancher disparaît sur le chemin du cache.** Un succès de cache de
  `GetFolderAsync` rend un `FolderDto` sans `UidValidity` (0). Une évaluation qui suit de moins de 10 s une liste de la
  Boîte de réception voit 0, différent de la valeur relevée à la demande : `FloorOf` rend `null`, toute la Boîte de
  réception est attendue, et le rappel ne revient pas tant que l'historique n'est pas ingéré. Une demande faite sur un
  succès de cache enregistre 0, et la garde `UIDVALIDITY` est contournée. Les tests d'intégration ne le voient pas :
  `UseCaseFixture` simule `IResilientCacheService` (jamais de succès de cache). Correctif : porter `UidValidity` dans
  `FolderStatusCache`, ou lire STATUS frais pour le plancher ; test avec un vrai cache.
- **R2 (B2 → F1 → R2, troisième apparition) — un échec de remise sous le plancher n'est jamais lu.** Le plancher est
  l'`UIDNEXT` de la **demande**. Rappel posé depuis le détail après un rebond déjà arrivé (non classé), ou rebond rapide
  arrivé entre l'envoi SMTP et le relevé : l'accusé est sous le plancher, jamais classé, et le message non distribué
  revient « Sans réponse ». Les accusés hors Boîte de réception ne sont plus lus non plus. Le bon repère (envoi ou
  demande) dépend de l'arbitrage **AH1**.
- **R3 (règle 1b)** — la branche « le retour attend tant qu'il reste plus de 20 accusés » n'est prouvée que par un test
  unitaire : dans le test d'intégration, l'échec est le plus ancien accusé, donc lu au premier paquet ; `return allRead;`
  laisserait le test vert. Test attendu : plus de 20 accusés **avant** l'échec, aucun retour à la première évaluation,
  clôture à une suivante.

#### Suggestions

- S1 : un rappel échu sans plancher fait attendre toute la boîte à tous les autres ; évaluer chaque rappel contre son
  propre plancher.
- S2 : le relevé du plancher passe par `GetFolderAsync` (verrou de session, SELECT/SEARCH si le cache d'UID est périmé,
  purge des disparus) sur le chemin de la réponse d'envoi ; un STATUS seul suffit.
- S3 (lié à AH1) : redemander un rappel ouvert écrase son plancher ; une réponse arrivée entre les deux demandes et non
  ingérée n'est plus attendue.
- S4 : la relecture de la Boîte de réception a lieu avant la clôture sur réponse ; une exception d'acquisition du verrou
  saute la clôture et fait tomber `follow-ups/returned`.
- S5 : une erreur persistante (autre que NotFound) de `BuildEmlAsync` sur un accusé bloque désormais tout retour de la
  boîte, au lieu de retarder une classification.

#### Pourquoi la chaîne s'arrête

1. **Règle 13** : R1 et R2 sont la troisième apparition des bloquants B1 (fausse relance / retour bloqué par
   l'ingestion) et B2 (échec de remise manqué), déjà revenus une fois en récidive (F2/F3, F1). Les causes sont nouvelles à
   chaque reprise, mais le symptôme est le même : dans le doute, la règle arrête.
2. **Décision requise** : le correctif de R2 (et S3) dépend d'AH1. Le repère du plancher est l'envoi si toute réponse
   compte, la demande si seules les réponses postérieures à la demande comptent.

Question écrite : `questions/task-462.md`.

#### Arbitrage rendu — reprise 3 autorisée (décision humaine du 2026-11-20)

L'humain accepte les recommandations (AH1 à AH3, voir l'Objectif) et relance la chaîne.

#### À corriger par la reprise

- **R1** — porter l'`UIDVALIDITY` dans le chemin du cache (`FolderStatusCache`), ou relire un STATUS frais pour le
  plancher ; test d'intégration sur un vrai cache (succès de cache entre la liste et l'évaluation), vu rouge.
- **R2 + AH1** — le repère est la demande : relevé **avant** l'envoi SMTP pour un rappel posé à l'envoi (le rebond rapide
  est au-dessus) ; seules les réponses et les échecs arrivés après la demande clôturent le rappel (une réponse
  antérieure, ingérée ou non, ne le clôt plus). Tests d'intégration vus rouges : rebond rapide après l'envoi, réponse
  antérieure à une demande depuis le détail.
- **R3** — test d'intégration de la branche « le retour attend » : plus de 20 accusés non classés avant l'échec, aucun
  retour à la première évaluation, clôture « non distribué » à une suivante ; vu rouge (`return allRead;`).
- **AH2** — exclure les messages automatiques (`IsAutomatic`) des réponses, et ne compter que les expéditeurs parmi les
  destinataires À et Cc de l'envoi ; tests d'intégration vus rouges (réponse d'absence, message d'un tiers).
- **AH3** — clore sur échec de remise seulement si tous les destinataires sont en échec ; test d'intégration vu rouge
  (deux destinataires, un seul en échec : le rappel reste ouvert et revient).

### Passage 4 (revue anticipée, après reprise 3) — CHANGES REQUESTED, reprise 4

Relecteur indépendant sur le diff de la reprise 3 (api-mail `dc39d1d3..a3923a85`, 22 fichiers), N1 vérifié sur le code.
Mobile et weda2 inchangés depuis le passage 2.

**contract_impact** : api-mcp aucun impact ; client-mobile aucun impact ; client-angular IMPACT
(`AuditActionType` décodé par rang), adapté (arbre de travail, inchangé depuis le passage 2).

**DOD, scénario e2e** : `E2E-FOLLOWUP-001` inchangé, au catalogue à la version déclarée par les tests.

| Constat | Corrigé | Test d'intégration | Preuve rouge |
|---|---|---|---|
| R1 UIDVALIDITY, chemin du cache | oui | `OnACacheHitOfTheInbox_TheFloorHolds` | R13 |
| R2 + AH1 repère avant SMTP, fenêtre | code oui ; rebond rapide et filtre de date des échecs **sans test d'intégration** (N2) | `AReplyBeforeTheRequestFromTheDetail_DoesNotCloseIt` (réponse seulement) | AH1 (réponse seulement) |
| R3 retour différé | oui | `ManyReportsBeforeTheFailure_TheReturnWaits_ThenTheFailureClosesIt` | R14 |
| AH2 automatique, tiers | oui | `AnOutOfOfficeAutoReply_DoesNotCloseIt`, `AMessageFromAThirdParty_DoesNotCloseIt` | AH2a, AH2b, code d'avant |
| AH3 échec partiel | oui, mais par IMAP sur le chemin de la liste (N1) | `ADeliveryFailureOfOneRecipientOutOfTwo_KeepsItOpen`, `ADeliveryFailureOfAllRecipients_ClosesIt` | AH3, code d'avant |

Vérifié sans constat : les 3 sites de `FolderStatusCache` (entrées antérieures désérialisées à 0), les deux STATUS, le
repère sur tous les chemins d'envoi (direct, brouillon, réponse, confirmation différée, annule et remplace), les Cc,
la migration `20261121120000` (règle 7c), règles 12 et 14, aucune donnée de santé en log, aucun « ; » en commentaire.

#### Bloquants

- **N1 (né du correctif d'AH3) — la liste des messages fait de l'IMAP et peut échouer.** `ApplyAsync`, appelé à chaque
  page d'en-têtes par `OnlineMailDataProvider` et `OfflineMailDataProvider` sans garde, passe par `CloseAnsweredAsync`,
  donc `AllRecipientsFailedAsync` → `ReadFailedRecipientsAsync` → `BuildEmlAsync` : verrou de session, connexion,
  FETCH de l'accusé entier. Avant la reprise, `ApplyAsync` ne lisait que la base. Un rappel en échec partiel (AH3 : il
  reste ouvert) refait ce FETCH à chaque chargement d'Envoyés ou d'« À traiter » et à chaque évaluation, jusqu'à la
  clôture manuelle. Un `TimeoutException` du verrou ou un `OpenAsync` en échec fait échouer tout le `GET` de la liste.
- **N2 (récidive de R2) — preuves d'intégration demandées et absentes.** L'ordre « repère avant SMTP » n'est prouvé que
  par un test unitaire, et le Develop log l'a classé « limite assumée » sans décision humaine. Le test est faisable :
  envelopper `ISmtpService` (fournisseur externe) pour déposer un accusé dans la Boîte de réception juste après l'envoi
  réel. Le filtre de date des échecs (AH1, `MailFollowUpRepository`) n'a pas de test non plus. L'argument « sous le
  plancher » est faux quand la vue conversation a déjà classé l'accusé : rebond, le médecin ouvre la conversation, puis
  pose un rappel depuis le détail. Selon AH1, le rappel doit rester ouvert.

#### Suggestions

- AH3 : rapprocher aussi `Original-Recipient` (adresse telle qu'écrite par l'expéditeur) des À/Cc, en plus de
  `Final-Recipient`.
- R1 : avec 0 lu comme inconnu, `OnACacheHit…` prouve que le plancher tient, pas que la garde UIDVALIDITY agit sur le
  chemin du cache. Un repère relevé à UIDVALIDITY nul ne détecte jamais un changement ultérieur.
- Une vue de cache vieille de 10 s peut produire un « Sans réponse » passager (corrigé à la synchronisation suivante).
- Un accusé dont la relecture échoue toujours (`null`) bloque le retour de ce rappel indéfiniment (même famille que S5).
- `FindRepliesAsync` filtre la date en mémoire : pousser `ArrivalDate >= min(Since)` dans le SQL.
- `CaptureAnchorAsync` ajoute un `GetFolderAsync` avant chaque envoi avec rappel ; un STATUS suffirait (S2).

#### À corriger par la reprise

- **N1** — sortir l'IMAP d'`ApplyAsync` et du chemin de la liste. Extraire les destinataires en échec au **classement**
  de l'accusé, qui lit déjà l'EML (`DeliveryReportReader.ReadAsync`, classement de la vue conversation), et les
  persister. AH3 devient une décision en base, et l'évaluation n'a plus à relire l'accusé. Test d'intégration vu rouge :
  la liste d'Envoyés avec un rappel en échec partiel reste 200 quand l'accusé n'est plus lisible sur le serveur.
- **N2 (récidive)** — tests d'intégration vus rouges : rebond rapide arrivé pendant l'envoi SMTP (mutation : repère
  relevé après SMTP), et échec déjà classé avant une demande depuis le détail (mutation : filtre de date retiré).

#### Arbitrage humain

Aucun.

#### Comptage (règle 13)

R2 a été la troisième apparition de B2 au passage 3 ; l'humain a relancé la chaîne le 2026-11-20. N2 est la première
apparition de R2 depuis cette relance : récidive tolérée une fois. Si un constat de cette lignée revient encore, la
chaîne s'arrête.

#### Amélioration continue

- N2 : une preuve exigée par la revue a été déclassée en « limite assumée » par la forge. La consigne est désormais dans
  `agents/develop.md`, « Mode reprise », point 3 : seul l'humain transforme une preuve exigée en limite acceptée.
- N1 : le point 6 du même mode (« qu'est-ce que le correctif casse ailleurs ? ») existait déjà. Récidive de lecture :
  la reprise 4 relit les appelants d'`ApplyAsync` avant de rendre la main.

### Passage 5 (revue anticipée, après reprise 4) — APPROVED

> **Revue faite par la forge elle-même, sur décision humaine du 2026-11-21** (« fais la revue et continue la chaîne »).
> Le relecteur indépendant s'est arrêté sur la limite d'usage hebdomadaire, avant tout verdict. L'auteur des reprises 3
> et 4 relit donc son propre code : l'humain en tient compte au merge (HAG).

Diff relu : api-mail `a3923a85..be75a84f` (15 fichiers). Mobile et weda2 inchangés depuis le passage 2.

**approved at** :
- api-mail `be75a84f` ;
- client-mobile `82fc95e` ;
- client-angular : arbre de travail non commité, inchangé depuis le passage 2 (31 entrées).

**contract_impact** :
- api-mcp : aucun impact ;
- client-mobile : aucun impact ;
- client-angular : IMPACT (`AuditActionType` décodé par rang), adapté dans l'arbre de travail.

**DOD, scénario e2e** : `E2E-FOLLOWUP-001` inchangé.

**Ce que le correctif a pu casser** (lu en premier) :
- `SetReportAsync` n'a qu'un appelant de production, le lecteur d'accusés, mis à jour. La vue conversation lit toujours
  `GetReportsAsync`, intact.
- `ReadFailedRecipientsAsync` n'a plus aucune référence.
- `DeliveryFailureReport` n'est consommé que par `CloseAnsweredAsync`.
- `ApplyAsync` ne contient plus aucun appel IMAP ni au lecteur d'accusés : il ne lit que la base, comme avant la reprise 3.
- `Original-Recipient` ne fait qu'ajouter l'adresse d'un groupe déjà en échec. Il ne peut pas faire clore à tort.
- Un rapport d'échec sans adresse lisible est gardé à `NULL`. Il ne clôt pas un rappel dont les destinataires sont
  connus : le rappel revient à l'échéance, comme au code de la reprise 3.

| Constat | Corrigé | Test d'intégration | Preuve rouge |
|---|---|---|---|
| N1 la liste relisait le rapport sur le serveur | oui (adresses gardées au classement, décision en base) | `AFailureClassifiedThenGoneFromTheServer_TheListStillClosesIt` | rouge sur le code de la reprise 3, mutation N1 (6 rouges) |
| N2 rebond rapide | oui (repère avant SMTP, déjà en place) | `ARapidBounceDuringTheSmtpSend_ClosesIt` (SMTP réel, puis rebond déposé avant le retour de l'envoi) | mutation N2a |
| N2 échec antérieur à la demande | oui (filtre de date, déjà en place) | `AFailureClassifiedBeforeTheRequestFromTheDetail_DoesNotCloseIt` | mutation N2b |

Le banc du rebond construit `OutgoingMailService` par `ActivatorUtilities` sur le scope de la fixture, avec ses vraies
dépendances. Seul le SMTP est enveloppé : c'est un fournisseur externe, que la règle 1b permet de simuler.

**Migration `20261121150000` (règle 7c)** : une colonne `text` nullable, aucune donnée modifiée ni supprimée, une descente,
le mapping EF par la constante.

**Règles 12 et 14** : rien de neuf. Aucune donnée de santé en log, aucun « ; » en commentaire.

#### Suggestions (non bloquantes, à porter dans la PR)

- **Vue Boîte de réception servie par le cache (10 s).** Une réponse arrivée dans ces 10 s et pas encore ingérée peut
  faire revenir le rappel une fois. Il est clos à la synchronisation suivante.
- **Filtre de date en mémoire.** `FindRepliesAsync` filtre la date en mémoire : pousser `ArrivalDate >= min(Since)` dans
  le SQL.
- **Coût du repère.** `CaptureAnchorAsync` relit le dossier (`GetFolderAsync`) avant chaque envoi qui porte un rappel. Un
  STATUS suffirait (S2).
- **Portée du test R1.** Il prouve que le plancher tient sur un succès de cache, pas que la garde UIDVALIDITY agit sur ce
  chemin.

#### Arbitrage humain

Aucun.

## Timings

*(généré par `tools/timing/report.sh --task task-462 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 2 min 17 s | — | — | — | — |
| /develop | ok | 19 min 18 s | 18 (2 min 54 s) | 16 (1 h 02 min) | — | dtos-mss 1B/0T, api-mail 12B/9T, client-mobile 3B/4T, client-angular 2B/3T, reprise 4 |
| /review-code | ok | 17 h 44 min | — | — | — | passage 5, revue par la forge (décision humaine) |
| /sonar | ok | 24 min 41 s | 2 (1 min 31 s) | 10 (17 min 52 s) | 4 (1 min 33 s) | 2 itération(s), api-mail 2B/10T |
| /lint-angular | ok | 1 min 37 s | — | — | — | 0 error, rien à corriger |
| **Total cycle** | | **18 h 32 min** | **20 (4 min 26 s)** | **26 (1 h 20 min)** | **4 (1 min 33 s)** | |

Autres commandes mesurées : lint ×1 (51 s), nuget-wait ×1 (29 s), restore ×1 (3.6 s)
