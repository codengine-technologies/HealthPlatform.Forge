# todo-task-381.md — Un refus métier d'api-mail s'affiche une seule fois, avec son vrai motif ; l'accusé de lecture repose sur le type de dossier

**Repos**: client-angular, api-mail (catalogue e2e `Api/Mail/e2e/scenarios.yml` seulement)
**Dependencies**: task-370 (intercepteurs d'authentification et d'erreur, mêmes fichiers)
**Epic**: E009
**Single frontend**: true
**Priorité**: **3** — messages contradictoires (« Accès refusé » générique en plus du motif réel), et accusé de lecture proposé ou omis selon le nom des dossiers.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-68, ANG-72**).

## Ce qui est établi

- **ANG-68** — `apps/weda2/src/app/core/interceptors/error.interceptor.ts:88-118` ajoute un toast générique (« Accès refusé. Vous n'avez pas les permissions nécessaires. », « Service temporairement indisponible ») aux réponses problem+json d'api-mail que le module traite déjà (403 `MAILBOX_PSC_MISMATCH`, refus d'auteur de task-367, 503 du proxy PSC). `mss-mailbox-management.component.ts:326-332` contourne déjà ce défaut en évitant des appels.
- **ANG-72** — `libs/mss/src/core/utils/read-receipt.util.ts` reconnaît le dossier des envoyés par `folderPath.includes('sent')` : un dossier « Consentements » ou « Présentation » ne propose jamais l'accusé ; la copie d'un envoi rangée dans « Envoyés » ou « Éléments envoyés » propose au médecin de s'envoyer un accusé. *Origine : zones 3 et 5.*

## Objective

Qu'un refus métier d'api-mail soit annoncé **une seule fois**, par l'écran qui sait l'expliquer, et que la proposition d'accusé de lecture dépende du **type** du dossier (SPECIAL-USE) et non de son nom.

### Périmètre

1. **`errorInterceptor`** : pas de notification générique pour une réponse d'api-mail portant un problem+json avec `code` (le module s'en charge), ou mécanisme d'exclusion par `HttpContextToken` ; le contournement de `mss-mailbox-management` est retiré.
2. **Accusé de lecture** : `FolderType.Sent` (et les autres types spéciaux) à la place de la comparaison de nom.

## Definition of Done

- [ ] Build et tests weda2 verts
- [ ] Tests unitaires rouges d'abord :
  - [ ] 403 `MAILBOX_PSC_MISMATCH` d'api-mail : aucune notification générique ; un 403 sans `code` d'un autre service garde la notification
  - [ ] mail reçu rangé dans un dossier nommé « Consentements » : l'accusé est proposé ; copie d'un envoi dans le dossier de type Sent nommé « Éléments envoyés » : il ne l'est pas
- [ ] Scénario E2E-RECEIPT-001 versionné si son comportement attendu change (dossier utilisateur au nom contenant « sent ») — angular et mobile selon l'arbitrage du `/start`
- [ ] Aucune donnée de santé ajoutée aux journaux

## Manual Test Plan

1. Provoquer un 403 `MAILBOX_PSC_MISMATCH` (carte d'un autre praticien) → un seul message, celui du module.
2. Déplacer dans un dossier « Consentements » un mail qui demande un accusé, l'ouvrir → l'accusé est proposé.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée ; le motif d'un refus PSC est affiché sans contradiction
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé (l'accusé reste tracé à l'envoi ou au refus, task-340)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable
- **AIPD / impact RGPD** : inchangé
- **MSSanté** : accusé de lecture (RFC 8098) proposé selon le type SPECIAL-USE du dossier
