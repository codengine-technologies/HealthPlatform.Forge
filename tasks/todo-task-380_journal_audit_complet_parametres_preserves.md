# todo-task-380.md — Le journal d'audit montre toutes les traces filtrées, et les paramètres du médecin ne sont jamais écrasés

**Repos**: client-angular, api-mail (catalogue e2e `Api/Mail/e2e/scenarios.yml` seulement)
**Dependencies**: — (aucune). Le filtre « type d'action » sans effet est un défaut serveur (`PostgresAuditReader.ApplyFilters`), suivi à part.
**Epic**: E009
**Single frontend**: true
**Priorité**: **2** — le journal d'imputabilité cache des actions, son export est incomplet et un extrait borné par dates manque des traces ; un échec de chargement des paramètres peut couper les alertes « biologie anormale » sans que le médecin le sache.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-59, ANG-60, ANG-61, ANG-62, ANG-78**).

## Ce qui est établi

- **ANG-59** — `mss-audit.component.ts:242-260` (`deduplicateByMailUid`) garde une trace par UID sur chaque page, sans tenir compte du dossier : « Lu », « Déplacé », « Supprimé » se réduisent à la dernière ; la page est retriée par date (le tri demandé est ignoré) ; l'export CSV (`:129-174`) n'exporte que la page dédoublonnée.
- **ANG-60** — `mss-audit.component.ts:75-78`, `audit-list.component.ts:44, 125-129` : appliquer un filtre perd « Erreurs uniquement » et le tri, et la pagination affichée ne correspond plus à la page chargée.
- **ANG-61** — `audit-filter.component.ts:38-41, 96-101` : les dates personnalisées sont lues en UTC ; aux Antilles, tout le dernier jour est exclu ; « aujourd'hui » n'est pas sélectionnable entre 00:00 et 02:00.
- **ANG-62** — `mss-settings.component.ts:120, 389-410, 460-482` : un échec de chargement affiche les valeurs par défaut, et le premier réglage touché les enregistre toutes (notifications coupées, identité d'expéditeur vide) ; un échec d'enregistrement arrête l'enregistrement automatique pour de bon.
- **ANG-78** — l'aperçu d'une trace peut afficher le mail d'une autre ; la recherche patient promet « nom, prénom, INS » mais ne cherche que le nom.

## Objective

Que le journal d'audit montre **toutes** les traces correspondant aux filtres affichés, dans l'ordre demandé, sur la période choisie en heure locale, avec un export complet ; et que les paramètres du médecin **ne soient jamais remplacés** par des valeurs par défaut à la suite d'une panne.

### Périmètre

1. **Journal** : plus de dédoublonnage (la vue par mail existe déjà via la frise par Message-ID) ; tri respecté ; filtre fusionné et non remplacé ; page pilotée par le parent ; dates construites en heure locale ; export sur tout le filtre (côté serveur si besoin, en accord avec l'équipe api-mail) ; aperçu annulable et vérifié par Message-ID.
2. **Paramètres** : édition bloquée et message tant que le chargement n'a pas réussi ; erreur d'enregistrement visible, enregistrement automatique qui reprend.
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
- [ ] Scénario E2E-AUDIT-001 « Le journal d'audit montre chaque action sur un mail » ajouté (angular `requis` ; mobile : `requis` si l'écran d'audit existe sur mobile, à confirmer)
- [ ] Scénario E2E-SETTINGS-003 « Paramètres indisponibles : rien n'est écrasé » ajouté (angular `requis`)
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
