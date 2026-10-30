# todo-task-415 — Rattachement, registre et identité de la boîte

**Repos**: api-mail, client-angular
**Dependencies**: task-407 (l'identité d'expéditeur de la boîte alimente le `From`)
**Epic**: E020

> **Origine** : audit du périmètre « boîte déléguée » du 2026-10-30
> (`Docs/audits/2026-10-30-audit-boite-deleguee.md`). Constats M9, M11, M14, m13 et les mineurs du
> registre.
>
> **Décisions humaines du 2026-10-30** :
> - M9 : **titulaire seul, toujours** ;
> - M10 (requalification et exemption du titulaire) : **inchangé**, risque accepté et documenté ;
> - M13 (reprise des données d'avant task-404) : **pas de reprise**, aucune base en production.

## Objectif

Seul le titulaire décide du nom sous lequel sa boîte écrit. Le rôle et l'identité d'une boîte
viennent de l'Annuaire, lu en entier. Les cas limites du registre rendent un résultat juste :
annuaire tronqué, adresse qui change de type, boîte en échec, rattachements simultanés.

## Règles

1. **Identité d'expéditeur : titulaire seul** (M9). Seul le titulaire de la boîte (rôle `Holder`)
   modifie son identité d'expéditeur. Sans titulaire actif, personne ne la modifie : elle reste celle
   préremplie depuis l'Annuaire (task-409). Le repli « aucun titulaire actif » est retiré, côté
   serveur et dans l'écran (champ en lecture seule).
2. **Identité d'une adresse organisationnelle** (M14). Le préremplissage d'un membre prend la raison
   sociale que l'Annuaire publie **pour l'adresse** de la boîte, et non la structure personnelle du
   membre (task-409, règle 3).
3. **Annuaire lu en entier** (m13). Une recherche LDAP tronquée par la limite de taille est
   **indisponible** (`UnavailableException`), comme une réponse FHIR incomplète. Elle ne requalifie
   pas, et ne fait ni refus ni acceptation.
4. **weda2 : pas de saisie préremplie avec sa propre adresse** (M11). Pendant le chargement de
   l'Annuaire, ou s'il est indisponible, l'adresse désignée par Weda n'est pas proposée dans le champ
   « BAL déléguée ». Le formulaire dit que la liste « Mes boîtes » est indisponible et propose de
   réessayer. Le serveur reste inchangé : une délégation sans contrôle de liste reste acceptée quand
   l'Annuaire est injoignable (task-402).
5. **Requalification** :
   - elle tient compte du **type d'adresse** : une adresse personnelle donne le rôle de titulaire, une
     adresse organisationnelle celui de membre. Une adresse personnelle devenue organisationnelle ne
     garde pas de titulaire ;
   - une requalification par l'Annuaire d'une boîte en échec enregistre aussi le succès de la sonde :
     la boîte redevient utilisable.
6. **Rattachements simultanés** : deux premiers rattachements en parallèle d'un même compte
   aboutissent tous les deux. Plus de faux 409 « déjà rattachée ».
7. **Contexte** :
   - `UserContextInfo.Reset()` efface aussi la boîte, le rôle et le nom de la personne. Le test de
     parité couvre tous les types de propriétés ;
   - une requête sans personne (contournement de test) n'efface pas l'identité d'expéditeur de la
     boîte.
8. **Documenté sans code** :
   - M10 (le titulaire n'est requalifié qu'en réauthentification, et reste exempté du verdict de
     l'opérateur) : risque accepté. À consigner dans la section Contraintes de `Docs/epics/E020-*` ;
   - M13 : pas de reprise des données d'avant task-404, aucune base en production à ce jour.

## Definition of Done

- [ ] Build passes (0 errors) sur `api-mail` et `client-angular` (code-only)
- [ ] Tests pass (0 failures)
- [ ] Unit tests :
  - droit d'édition de l'identité (titulaire, délégataire, membre, aucun titulaire) ;
  - LDAP tronqué indisponible ;
  - requalification par type d'adresse ;
  - `Reset()` et la parité de copie.
- [ ] Test d'intégration de bout en bout pour `PUT …/mailboxes/current/sender-identity`, **deux
      personnes sur la même boîte**, sans titulaire actif : le délégataire reçoit le refus
      (problem+json), et l'identité relue est inchangée. Vu rouge (règle 1b).
- [ ] Test d'intégration de bout en bout : le premier membre d'une adresse organisationnelle dont la
      BAL personnelle est dans un autre cabinet. L'identité relue de la boîte porte la raison sociale
      publiée pour l'adresse organisationnelle. Vu rouge.
- [ ] Test d'intégration de bout en bout sur le vrai OpenLDAP du banc, avec une limite de taille
      atteinte : la réauthentification garde le rôle, et le rattachement par « Mes boîtes » répond
      indisponible (503). Vu rouge.
- [ ] Test d'intégration de bout en bout : une adresse publiée en ORG alors que la personne en est
      titulaire. Après réauthentification, son rôle relu est membre. Vu rouge.
- [ ] Test d'intégration de bout en bout : la requalification par l'Annuaire d'une boîte en échec
      rend une boîte sélectionnable (`GET /account/mailboxes`). Vu rouge.
- [ ] Test d'intégration de bout en bout : deux premiers rattachements concurrents donnent 201 et
      201, et deux boîtes relues. Vu rouge.
- [ ] weda2 : test de composant. Annuaire en chargement ou indisponible : le champ délégation est
      vide, et le message d'indisponibilité est affiché.
- [ ] Scénario **E2E-MAILBOX-003 v3** (mobile requis, angular requis). Annuaire indisponible :
      « Mes boîtes » dit l'indisponibilité, et l'adresse désignée n'est pas préremplie en délégation.
      Implémenté dans chaque client. Côté mobile, le test confirme le comportement déjà conforme.
- [ ] `Docs/epics/E020-*.md` : M10 et M13 consignés dans « Contraintes et hypothèses »
- [ ] Évènements PGSSI-S journalisés : refus de modification de l'identité de la boîte (personne,
      rôle) ; requalification

## Manual Test Plan

- Backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil e2e). weda2 via le faux hôte.
- Détacher le titulaire e2e de `boite-praticien`. Le délégataire ouvre les réglages. Attendu : le nom
  d'expéditeur est en lecture seule, et un `PUT` répond par un refus.
- Couper l'Annuaire simulé, puis ouvrir weda2 sur une boîte désignée par Weda. Attendu : « Mes boîtes
  indisponible », et le champ délégation vide.
- Annuaire de test « partenaires » (LDAP) avec `SizeLimit` = 1 : la réauthentification garde le rôle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur
- **Exigences DSR honorées** : référentiel socle MSSanté #2 (clients), ECO.1.2.9. Le nom du `From`
  est celui de la boîte, décidé par son titulaire.
- **INS** : non applicable
- **Authentification PS** : PSC. Le rôle vient de l'Annuaire pour le RPPS du jeton.
- **Habilitations** :
  - titulaire seul pour l'identité de la boîte ;
  - rôle par type d'adresse (PER donne titulaire, ORG donne membre), règle 14 ;
  - exemption du titulaire inchangée (M10, décision humaine).
- **Interop CI-SIS** : non applicable — Annuaire Santé FHIR et annuaire MSSanté LDAP
- **Tracé PGSSI-S** : refus de modification de l'identité, requalification, rattachements.
  Conservation 3 653 jours.
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — registre de la plateforme
- **AIPD / impact RGPD** : inchangé
