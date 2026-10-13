# todo-task-377.md — Liste, recherche et puce « Bio à acquitter » montrent ce qu'elles annoncent, et disent quand elles ne peuvent pas

**Repos**: client-angular, api-mail
**Dependencies**: task-375 (identité `(folderPath, uid)` et flux de chargement de la liste)
**Epic**: E009
**Single frontend**: true
**Priorité**: **2** — des résultats de biologie à acquitter sont masqués alors que le compteur dit qu'ils existent ; une panne fait disparaître la tuile au lieu de la signaler ; la vue « Mails du patient » s'interrompt d'elle-même au bout de 30 s.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-31, ANG-32, ANG-33, ANG-35, ANG-37**).

## Ce qui est établi

- **ANG-31** — `inbox-biology-ack-chip.component.ts:73-125`, `mail-state.service.ts:280-300` : la puce filtre seulement la page chargée, garde les UID d'INBOX dans les autres dossiers, et peut laisser l'INBOX filtrée sans aucun signe visible après un retour de lecture.
- **ANG-32** — `isSearchActive` n'est jamais remis à zéro : pagination disparue (50 premiers messages seulement), recherche effacée qui revient, résultats d'une ancienne recherche affichés en dernier, nouveaux messages ajoutés aux résultats.
- **ANG-33** — `mss-mail.component.ts:815-864` : la vue « Mails du patient » est un dossier virtuel `__patient__/{id}` ; le rafraîchissement le demande à api-mail (404 `FOLDER_NOT_FOUND`) et renvoie à INBOX avec un faux « dossier supprimé depuis un autre logiciel » ; une seule page ; le handle du patient part dans l'URL, les journaux serveur et le SSE.
- **ANG-35** — sans volet de lecture (réglage par défaut), « Version précédente » d'un CDA versionné ne fait rien, et le bouton « IA » détourne la prochaine lecture vers une conversation construite sur d'autres messages.
- **ANG-37** — une erreur masque la tuile « biologie en attente » (le tableau de bord ressemble à « rien en attente ») ; un échec des réglages bloque la messagerie sur un spinner.

## Objective

Que la liste, la recherche, la vue patient et les indicateurs de biologie montrent **exactement** ce qu'ils annoncent — tous les résultats à acquitter, tous les mails du patient, les seuls résultats de la recherche affichée — et qu'une panne soit **signalée** comme telle, jamais confondue avec « rien à signaler ».

### Périmètre

1. **Puce « Bio à acquitter »** servie par le serveur comme une source paginée (comme la recherche), rechargée au changement de dossier, état actif tenu par l'état de la liste.
2. **Recherche** remise à zéro au changement de dossier ; « effacer » annule la requête en vol ; pas d'ajout de nouveaux messages pendant une recherche.
3. **Vue « Mails du patient »** avec sa propre source (hors rafraîchissement de dossier, SSE et puce), paginée côté serveur ; le handle du patient n'apparaît jamais dans un chemin d'URL.
4. **Sans volet de lecture** : « Version précédente » et l'assistant IA fonctionnent (abonnement porté par l'écran mail, `folderPath` respecté) ; l'IA se ferme au changement de dossier.
5. **États « indisponible »** explicites (tuile, puce, écran) avec réessai.

## Definition of Done

- [ ] Build et tests verts : weda2, api-mail
- [ ] Test d'intégration de bout en bout pour la liste paginée des mails à biologie non acquittée (route existante ou ajoutée) : 60 mails en attente sur deux pages, la page 2 contient les 10 derniers (lus dans la réponse réelle), vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout pour la liste paginée des mails d'un patient, désigné par son handle dans le corps ou la requête et non dans le chemin : la page 2 existe et le handle n'apparaît pas dans le chemin journalisé, vu rouge (règle 1b) — si la route est créée ou modifiée
- [ ] Tests unitaires et de composant rouges d'abord :
  - [ ] puce active sur la page 3 : les résultats en attente de toutes les pages sont accessibles
  - [ ] changement de dossier pendant une recherche : recherche et pagination remises à zéro
  - [ ] vue patient ouverte 60 s : ni retour à INBOX ni message « dossier supprimé »
  - [ ] sans volet de lecture : « Version précédente » ouvre la version précédente
  - [ ] erreur du résumé de biologie : la tuile affiche « indisponible » et un réessai
- [ ] Scénario E2E-BIO-002 « La puce Bio à acquitter montre tous les résultats en attente, sur toutes les pages » ajouté (angular `requis` ; mobile : `non-applicable` si la puce n'existe pas sur mobile, à confirmer)
- [ ] Scénario E2E-PATIENT-001 versionné : la vue « Mails du patient » reste ouverte et paginée
- [ ] Trou du filet : ligne dans `conventions/e2e.md`
- [ ] Aucun handle patient, INS ni contenu dans les URL et journaux ajoutés

## Manual Test Plan

1. Boîte avec plus de 50 mails dont des biologies non acquittées réparties sur plusieurs pages : activer la puce → toutes apparaissent, sur toutes les pages.
2. Rechercher « échographie », changer de dossier → la recherche est effacée, la pagination revient.
3. Ouvrir « Mails du patient » depuis le tableau de bord, attendre 2 min → la vue reste ouverte ; parcourir plusieurs pages.
4. Couper api-mail : la tuile « biologie en attente » affiche « indisponible », pas une absence.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : biologie / médecine de ville
- **Vague Ségur** : hors Ségur — correctif
- **Exigences DSR honorées** : non applicable — rétablit l'exhaustivité de l'affichage des résultats à acquitter
- **INS** : non applicable ; le handle patient sort des URL (cohérent avec task-184)
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : résultats de biologie (CDA, LOINC) — affichage seulement
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : non applicable
- **Référentiels métier** : LOINC (biologie)
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé
