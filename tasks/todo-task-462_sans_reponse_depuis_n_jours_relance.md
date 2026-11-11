# todo-task-462.md — Sans réponse depuis N jours : relance

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Dependencies**: done-task-454 (vue « À traiter »), done-task-459 (détection des réponses), done-task-460 (rapports
exclus)
**Epic**: E024
**Priorité**: EPIC E024, demandée par l'humain le 2026-11-11. Douleur n° 5 (2/5). Une demande d'avis restée sans
réponse est une boucle de coordination non fermée, donc un risque de soins.

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
- **Échec de remise** (task-460) : un envoi en échec ne pose pas de rappel ; l'échec est déjà dans « À traiter ».
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
