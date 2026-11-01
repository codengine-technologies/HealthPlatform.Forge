# todo-task-380.md — Le journal d'audit montre toutes les traces filtrées, et les paramètres du médecin ne sont jamais écrasés

**Repos**: client-angular, api-mail (catalogue e2e `Api/Mail/e2e/scenarios.yml` seulement)
**Dependencies**: — (aucune). Le filtre « type d'action » sans effet, défaut serveur de `PostgresAuditReader.ApplyFilters`, a été corrigé par task-405 (archivée) : `ActionType`, `Search` et le filtre par personne sont appliqués côté serveur.
**Epic**: E009
**Single frontend**: true
**Priorité**: **2** — le journal d'imputabilité cache des actions, son export est incomplet et un extrait borné par dates manque des traces ; un échec de chargement des paramètres peut couper les alertes « biologie anormale » sans que le médecin le sache.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-59, ANG-60, ANG-61, ANG-62, ANG-78**).

## Ce qui est établi

> **Revérifié le 2026-11-01** sur weda2 `feature/nova-mss-weda-integration` (`35b5163c`, 2026-10-30),
> après les tasks 384, 403, 404 et 405 qui ont touché ces fichiers. Les cinq défauts sont toujours
> présents ; les numéros de ligne ci-dessous sont ceux de cette révision.

- **ANG-59** — `mss-audit.component.ts:242-260` (`deduplicateByMailUid`, appelé `:224`) garde une trace par UID sur chaque page, sans tenir compte du dossier : « Lu », « Déplacé », « Supprimé » se réduisent à la dernière ; la page est retriée par date (le tri demandé est ignoré) ; l'export CSV (`:129-163`) n'exporte que `traces()`, la page dédoublonnée. Aucun endpoint d'export n'existe côté api-mail.
- **ANG-60** — `mss-audit.component.ts:75-78` remplace le filtre au lieu de le fusionner : `success` repart de la liste déroulante du filtre (`audit-filter.component.ts:93`), `sortBy`/`sortDirection` sont perdus. `audit-list.component.ts:46-50` garde ses propres `errorOnly`, `currentPage` et tri, jamais réinitialisés par le parent : le bouton « Erreurs uniquement » reste actif et la pagination affiche une autre page que celle chargée.
- **ANG-61** — `audit-filter.component.ts:40-43` (`todayIso` en UTC) et `:97-105` : `new Date('AAAA-MM-JJ')` est minuit UTC. En UTC−4, la période du 01/10 au 01/10 couvre du 30/09 20:00 au 30/09 23:59 locales, et toute la journée choisie est exclue. Entre 00:00 et 02:00 en métropole, « aujourd'hui » dépasse le `max` du sélecteur.
- **ANG-62** — `mss-settings.component.ts:120-123, 402-420, 519-541` : un échec de `getUserSettings` laisse `DEFAULT_SETTINGS` à l'écran (alertes, dont « biologie anormale », toutes à `false`), sans message et sans blocage ; le premier réglage touché les POSTe toutes. L'erreur du `switchMap` termine le flux d'enregistrement automatique : plus rien n'est enregistré jusqu'au rechargement.
  - **Changé par task-404** : l'identité d'expéditeur ne passe plus par `saveUserSettings`. Elle a sa route (`getMailboxSenderIdentity` / `saveMailboxSenderIdentity`, `:486-511`), et un échec de chargement la verrouille (`canEdit = false`) : elle n'est plus écrasée par des valeurs vides. **Même défaut d'enregistrement** en revanche : un échec bascule le champ en lecture seule, sans message, et termine son flux d'enregistrement.
- **ANG-78** — l'aperçu d'une trace (`mss-audit.component.ts:186-199, 296-308`) n'annule pas la requête précédente et ne vérifie pas le Message-ID du mail reçu : il peut afficher le mail d'une autre trace. La recherche patient (`patient-search.component.html:7`) promet « nom, prénom, INS… » mais `searchPatients` n'envoie que `lastName` (`mss-api.service.ts:1360`).
- **Mobile** : pas d'écran de journal (cf. E2E-AUDIT-001). Ses paramètres ne sont pas concernés par ANG-62 : `user-settings.service.ts` n'enregistre rien tant que le chargement n'a pas réussi, et un échec d'enregistrement ne coupe pas le flux.

## Objective

Que le journal d'audit montre **toutes** les traces correspondant aux filtres affichés, dans l'ordre demandé, sur la période choisie en heure locale, avec un export complet ; et que les paramètres du médecin **ne soient jamais remplacés** par des valeurs par défaut à la suite d'une panne.

### Périmètre

1. **Journal** : plus de dédoublonnage (la vue par mail existe déjà via la frise par Message-ID) ; tri respecté ; filtre fusionné et non remplacé ; page pilotée par le parent ; dates construites en heure locale ; export sur tout le filtre (côté serveur si besoin, en accord avec l'équipe api-mail) ; aperçu annulable et vérifié par Message-ID.
2. **Paramètres** : édition bloquée et message tant que le chargement n'a pas réussi ; erreur d'enregistrement visible, enregistrement automatique qui reprend. Même traitement pour l'enregistrement de l'identité d'expéditeur (task-404).
3. **Recherche patient** : l'invite décrit ce qui est réellement cherché.

## Definition of Done

- [ ] Build et tests weda2 verts
- [ ] Tests unitaires et de composant rouges d'abord :
  - [ ] trois traces du même mail sur une page : les trois sont affichées ; deux traces de même UID dans deux dossiers aussi
  - [ ] tri par action : l'ordre affiché est celui du serveur
  - [ ] « Erreurs uniquement » activé puis changement de période : le filtre d'erreurs est conservé ; la page revient à 1
  - [ ] période du 01/10 au 01/10 en UTC−4 : les bornes envoyées couvrent la journée locale entière
  - [ ] échec de chargement des paramètres : formulaire désactivé, message affiché, aucun POST
  - [ ] échec d'enregistrement : message affiché, la modification suivante est enregistrée
  - [ ] échec d'enregistrement de l'identité d'expéditeur : message affiché, la modification suivante est enregistrée
  - [ ] aperçu : deux traces sélectionnées à la suite, la réponse de la première arrive en dernier → c'est le mail de la seconde qui est affiché
- [ ] Scénario E2E-AUDIT-002 « Le journal d'audit montre chaque action sur un mail » ajouté (angular `requis` ; mobile `non-applicable` — pas d'écran de journal). E2E-AUDIT-001 est pris par task-405.
- [ ] Scénario E2E-SETTINGS-004 « Paramètres indisponibles : rien n'est écrasé » ajouté (angular `requis` ; mobile `non-applicable` — le client mobile n'enregistre rien sans chargement réussi). E2E-SETTINGS-003 est pris par task-384.
- [ ] Aucune donnée de santé ajoutée aux journaux

## Manual Test Plan

1. Lire, déplacer puis supprimer un mail ; ouvrir le journal → trois traces.
2. Trier par action → l'ordre suit la colonne ; exporter → le fichier contient toutes les traces du filtre.
3. Filtrer « Erreurs uniquement », changer de période → seules les erreurs restent affichées.
4. Rendre `getsettings` indisponible (api-mail arrêtée), ouvrir les paramètres → message d'erreur, rien n'est modifiable ; relancer api-mail → les vrais paramètres s'affichent, intacts.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif
- **Exigences DSR honorées** : non applicable — rétablit l'exhaustivité de la consultation du journal PGSSI-S
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : le journal reste cloisonné par boîte (inchangé)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : la consultation des traces devient exhaustive ; aucune trace nouvelle
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — le journal porte des métadonnées de mails
- **AIPD / impact RGPD** : inchangé
