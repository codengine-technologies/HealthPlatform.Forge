# todo-task-461.md — Adresse déjà en échec signalée à la saisie

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Dependencies**: done-task-460 (lecture des avis de non-remise)
**Epic**: E024
**Priorité**: EPIC E024, demandée par l'humain le 2026-11-11. Douleur n° 4 (3/5) : la recherche dans l'annuaire est
excellente, mais rien ne dit **quelle adresse fonctionne**.

> **Origine.** Analyse du 2026-11-11, manque D2.

## Ce qui est établi

- Autocomplétion :
  - `GET api/v1/Contact/search?q=` (`ContactController.SearchAsync`) ;
  - `GET api/v1/Directory/practitioners/search` (`DirectoryController`, Annuaire Santé FHIR ou LDAP) ;
  - côté clients : `searchContacts` et `searchPractitioners` (`mss-api.service.ts` weda2 et mobile), appelés par
    `mail-compose.component.ts`.
- `ContactMssAddress` (adresse, adresse par défaut, ordre) ne couvre que les contacts enregistrés. Les résultats de
  l'annuaire ne sont pas conservés.
- L'annuaire affiche **toutes** les adresses MSS d'un praticien (task-386).

## Objective

Quand le praticien saisit un destinataire dont l'adresse a **déjà échoué** de façon définitive depuis cette boîte, il
le voit **avant d'envoyer**, avec le motif. Si l'annuaire connaît d'autres adresses du même praticien, elles lui sont
proposées.

Règles :
- **Seuls les échecs définitifs marquent une adresse** (codes 5.x : adresse inexistante, refus). Un échec temporaire
  (4.x) ou une boîte pleine (5.2.2) ne la marque pas.
- **Signal dans l'autocomplétion et sur l'étiquette du destinataire** :
  - « ⚠ Dernier envoi en échec le {date} : cette adresse n'existe pas » ;
  - si l'annuaire connaît une autre adresse de la même personne : « Autres adresses connues : … », choisissables
    d'un clic.
- **L'envoi reste possible** : le signal informe, il ne bloque pas.
- **Effacement** : le marqueur s'efface dès qu'un envoi ultérieur à cette adresse est délivré ou lu, ou quand le
  praticien choisit « Ne plus signaler » (geste imputé).
- **Par boîte** : le marqueur appartient à la boîte (règle 14), jamais partagé avec d'autres boîtes.

### Hors périmètre

- Signaler l'inactivité d'une adresse **avant** tout envoi : l'information appartient à l'annuaire national (BAL
  préférentielle de l'API FHIR, annoncée pour 2027).

## Definition of Done

- [ ] Marqueur par adresse normalisée dans la base de la boîte (migration FluentMigrator, audit règle 7c), alimenté
      par les échecs définitifs de task-460, effacé par une remise réussie.
- [ ] Contrat : marqueur (date, motif) sur les résultats de `Contact/search` et `Directory/practitioners/search` ;
      paquet DTO publié.
- [ ] Acte d'audit `RecipientWarningDismissed` (personne) ; pose et effacement automatiques en actes système.
- [ ] Tests unitaires : 5.1.1 marque, 4.x ne marque pas, 5.2.2 ne marque pas, remise réussie efface, « Ne plus
      signaler » efface.
- [ ] **Test d'intégration de bout en bout (règle 1b)** :
      - après un échec 5.1.1 relié (task-460), `GET api/v1/Contact/search?q=` puis `Directory/practitioners/search`
        rendent l'adresse avec son marqueur et son motif ;
      - un envoi délivré ensuite efface le marqueur ;
      - cas d'échec : un 4.x ne pose aucun marqueur.
      Vu rouge.
- [ ] Tests de composant (weda2 et mobile), vus rouges par mutation : signal dans l'autocomplétion, sur l'étiquette,
      autres adresses proposées, « Ne plus signaler ».
- [ ] **Scénario e2e** `E2E-COMPOSE-006` v1, mobile et angular requis, vu rouge : après un échec, saisir à nouveau
      l'adresse affiche « Dernier envoi en échec », et l'envoi reste possible.
- [ ] `data-testid`, conventions de libellés, aucune donnée de santé dans les logs.
- [ ] Build et tests verts (api-mail, Dtos, weda2, mobile) ; client-angular : code-only.

## Manual Test Plan

1. Reprendre l'envoi en échec du plan de test de task-460 (adresse inexistante).
2. Nouveau message : taper le début de cette adresse. La suggestion porte « ⚠ Dernier envoi en échec le … : cette
   adresse n'existe pas ».
3. Rechercher dans l'annuaire un praticien qui a deux adresses, dont une en échec : l'autre est proposée.
4. Choisir « Ne plus signaler » : le signal disparaît, et le journal de la boîte trace le geste.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — fiabilité de l'adressage
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — les adresses `@patient.mssante.fr` sont traitées comme les autres, sans que l'INS soit
  affichée en clair hors de l'adresse déjà saisie
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel
- **Habilitations** : personnes de la boîte sous verdict de l'opérateur (règle 14)
- **Interop CI-SIS** : Annuaire Santé (FHIR ou LDAP), inchangé
- **Tracé PGSSI-S** : `RecipientWarningDismissed` au nom de la personne ; pose et effacement en actes système ;
  `HealthDataAccess`, 3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : codes d'état SMTP (RFC 3463)
- **Hébergement HDS** : oui — base de la boîte
- **AIPD / impact RGPD** : inchangé — donnée technique sur une adresse professionnelle
