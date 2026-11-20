# todo-task-462.md — Sans réponse depuis N jours : relance

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
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

## Timings

*(généré par `tools/timing/report.sh --task task-462 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 2 min 17 s | — | — | — | — |
| /develop | ok | 1 h 51 min | 7 (1 min 12 s) | 6 (16 min 16 s) | — | dtos-mss 1B/0T, api-mail 3B/2T, client-mobile 2B/3T, client-angular 1B/1T |
| **Total cycle** | | **1 h 53 min** | **7 (1 min 12 s)** | **6 (16 min 16 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : nuget-wait ×1 (29 s), restore ×1 (3.6 s)
