# todo-task-001.md — En-tetes SMTP MSSante

**Repos**: api-mail
**Dependencies**: aucune

## Objectif

Lors de l'envoi d'un message MSSante, le systeme doit inserer les en-tetes SMTP
reglementaires definis dans le Referentiel socle MSSante #2 (v1.0.1, sections 3.8.1
a 3.8.3 et 3.4.2.3). Ces en-tetes permettent aux operateurs MSSante et a Mon Espace
Sante de traiter correctement les messages (statistiques, indicateurs, blocage reponse).

## Detail des en-tetes

### 1. `X-MSS-CODECDA` (ECO.2.4.1 — Ref#2 §3.8.1)

- **Quand :** message contenant en PJ un ou plusieurs documents CDA encapsules dans une archive IHE_XDM
- **Valeur :** le champ `code` present dans l'en-tete du document CDA (code type document CI-SIS, defini dans le Volet Structuration Minimale [CI-STRU-ENTETE])
- **Multi-value** si plusieurs documents CDA : valeurs separees par des virgules
- **Ne pas positionner** si absence de document CDA encapsule dans l'archive IHE_XDM
- Exemples :
  - `X-MSS-CODECDA: 34112-3`
  - `X-MSS-CODECDA: 34112-3,PRESC-BIO,15508-5`

### 2. `X-MSS-INS` (ECO.2.4.2 — Ref#2 §3.8.2)

- **Quand :** message contenant en PJ au moins un document CDA encapsule dans une archive IHE_XDM
- **Valeur :**
  - `O` (Oui) si presence d'une INS **qualifiee** dans l'archive IHE_XDM
  - `N` (Non) si absence d'INS qualifiee
- **INS qualifiee** = le document CDA contient le matricule INS **ET** son OID **ET** les 4 traits d'identite (nom de naissance, 1er prenom, date de naissance, sexe)
- **Ne pas positionner** si absence de document CDA en PJ
- Exemples :
  - `X-MSS-INS: O`
  - `X-MSS-INS: N`

### 3. `X-MSS-NIL` (ECO.2.4.3 — Ref#2 §3.8.3)

- **Quand :** **tous** les courriels envoyes, avec ou sans document medical
- **Valeur :** le numero « reference produit » attribue lors de la declaration du produit sur la plateforme `convergence.esante.gouv.fr`
- **Objectif :** permettre a l'operateur d'identifier le LPS emetteur et au gestionnaire de l'espace de confiance de suivre le deploiement

### 4. `X-MSS-MES` (ECO.2.2.8 — Ref#2 §3.4.2.3)

- **Quand :** messages envoyes vers un usager via Mon Espace Sante (adresse `<matriculeINS>@patient.mssante.fr`) **et** le professionnel souhaite bloquer la reponse du patient
- **Valeur :** `FIN` (3 caracteres en majuscules)
- **Effet :** MES empeche l'usager de repondre au professionnel

## Gherkin

See `tests/mss.mail.bdd.tests/Features/Mss/EntetesSmtpMssante.feature`

## Exigences Segur couvertes

- SC.MSS/CONF.14 (ECO.2.4.2) — X-MSS-INS
- SC.MSS/CONF.15 (ECO.2.4.1) — X-MSS-CODECDA
- SC.MSS/CONF.16 (ECO.2.4.3) — X-MSS-NIL
- SC.MSS/CONF.21 (ECO.2.2.8) — X-MSS-MES

## References reglementaires

- Referentiel socle MSSante #2 v1.0.1 (18/01/2024) — sections 3.8.1, 3.8.2, 3.8.3, 3.4.2.3
- Volet Structuration Minimale de Documents de Sante du CI-SIS [CI-STRU-ENTETE]
- Referentiel Identifiant National de Sante [INS-REF]

## Definition of Done

- [ ] Build passes (0 errors) sur `api-mail`
- [ ] Tests pass (0 failures)
- [ ] `X-MSS-CODECDA` positionne avec la valeur du champ `code` de l'en-tete CDA (multi-value si plusieurs CDA)
- [ ] `X-MSS-CODECDA` absent si pas de CDA en PJ dans l'archive IHE_XDM
- [ ] `X-MSS-INS` positionne a `O` si INS qualifiee (matricule INS + OID + 4 traits d'identite)
- [ ] `X-MSS-INS` positionne a `N` si INS non qualifiee mais CDA present
- [ ] `X-MSS-INS` absent si pas de CDA en PJ
- [ ] `X-MSS-NIL` positionne sur **tous** les messages avec la reference produit `convergence.esante.gouv.fr`
- [ ] `X-MSS-MES` positionne a `FIN` sur les messages vers `@patient.mssante.fr` quand le blocage reponse est active
- [ ] >= 1 test d'integration par scenario Gherkin
- [ ] Aucune regression sur les tests existants d'envoi

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Composer un message avec un document CDA rattache a un patient avec INS qualifiee
  - Verifier dans les logs SMTP : `X-MSS-CODECDA: <code CDA>`, `X-MSS-INS: O`, `X-MSS-NIL: <ref produit>`
- Composer un message avec CDA sans INS qualifiee
  - Verifier `X-MSS-INS: N`
- Composer un message avec 2 CDA de types differents
  - Verifier `X-MSS-CODECDA` multi-value (ex: `34112-3,PRESC-BIO`)
- Composer un message texte sans PJ
  - Verifier uniquement `X-MSS-NIL` present, pas de `X-MSS-CODECDA` ni `X-MSS-INS`
- Envoyer vers `@patient.mssante.fr` avec blocage reponse
  - Verifier `X-MSS-MES: FIN`
