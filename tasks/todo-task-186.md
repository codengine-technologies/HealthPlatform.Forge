# todo-task-186.md — Journal d'audit PGSSI-S incomplet : téléchargements de PJ non tracés, traces perdues sous charge

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axes confidentialité
> et concurrence). Vérifié par le PO.

> ### Re-vérification du 2026-08-23 — **toujours pertinente, intégralement**
>
> Chaque preuve rejouée sur `develop`. Les numéros de ligne du bloc « Preuve »
> datent du 2026-07-25 ; **la colonne « au 2026-08-23 » fait foi**.
>
> | Preuve | 2026-07-25 | Au 2026-08-23 | État |
> |---|---|---|---|
> | PJ unitaire non tracée | `MailController.cs:437` | **`:505`** (`…/download/attachment/{attachmentfilename}`) | inchangé |
> | Archive ZIP non tracée | `:495-570` | **`:592`** (`…/attachments/download/zip`) | inchangé |
> | `MailController` n'appelle jamais l'audit | — | **confirmé : 0 occurrence** de `auditService`/`IAuditService` dans le fichier | inchangé |
> | Aucun type d'action « pièce jointe » | énumération | **confirmé** — `Dtos/AuditActionType.cs` (le type vit dans `dtos-mss`) n'a **aucun** membre `Attachment*`/`*Download*` | inchangé |
> | Asymétrie avec l'export | `MailExportController.cs:142-154` | **`:88`** (EML) et **`:124`** (PDF/impression) tracent, via `TraceMailAction` | inchangé |
> | File bornée qui jette le plus ancien | `ServiceCollectionExtensions.cs:90-93` | **`:125-127`** — `BoundedChannelOptions(1000)` + `FullMode = DropOldest` | inchangé |
> | Retour de `TryWrite` ignoré | `AuditService.cs:45` | **`:59`** | inchangé |
> | Contrat inverse documenté | `AuditBackgroundService.cs:15` | **`:14`** (« no trace is lost ») et `:45`, `:48` (« the trail must be exhaustive ») | inchangé |
>
> **Note de périmètre découverte à la re-vérification** : le type d'action vivant
> dans `dtos-mss`, ajouter des membres à `AuditActionType` **touche un porteur de
> contrat** — la task devra lister `dtos-mss` dans `**Repos**:` et passer par
> `/publish-dtos`. Ce point n'était pas identifié au 2026-07-25.

## Objective

Rendre le journal d'audit **complet et fiable**, c'est-à-dire réellement opposable.
Deux défauts se composent, et ils se renforcent l'un l'autre :

1. **Trou de couverture** — les deux routes qui extraient des pièces jointes
   cliniques brutes de la plateforme (PJ unitaire et archive ZIP de toutes les PJ)
   ne produisent **aucune** trace d'audit. Un praticien — ou quiconque détenant un
   jeton valide — peut exfiltrer l'intégralité des pièces jointes d'une boîte sans
   laisser de trace journalisée.
2. **Perte silencieuse sous charge** — le canal d'audit est borné à 1000 éléments
   en mode `DropOldest`, et l'écriture ignore sa valeur de retour : dès que
   l'écriture dépasse la lecture, des traces **déjà acceptées** sont écartées, sans
   log, sans métrique, sans erreur.

Ensemble : un journal qui a des trous par conception et qui ne le dit pas.

**US backend-only (justification)** : journalisation côté serveur.

### Preuve (état actuel du code)

**Trou de couverture** :
- `src/Api/Controllers/V1/MailController.cs:437` (PJ unitaire) et l'endpoint
  d'archive ZIP autour de `:495-570` : `MailController` n'appelle **jamais**
  `auditService.Trace` — il est absent des treize fichiers qui le font.
- L'énumération `AuditActionType` n'a **aucun** membre relatif aux pièces jointes
  (les valeurs existantes couvrent `MailRead`, `MailExportPdf`, `MailExportEml`,
  `MailPrint`, `MailSend`, …).
- Asymétrie révélatrice : `src/Api/Controllers/V1/MailExportController.cs:142-154`
  journalise soigneusement l'export PDF, l'impression et l'export EML. Les deux
  routes fonctionnellement équivalentes — sortir un document clinique de la
  plateforme — ne le font pas. Oubli, non arbitrage.

**Perte silencieuse** :
- `src/Application/Extensions/ServiceCollectionExtensions.cs:90-93` :
  ```csharp
  services.AddSingleton(Channel.CreateBounded<MssAuditTrace>(new BoundedChannelOptions(1000)
  {
      FullMode = BoundedChannelFullMode.DropOldest
  }));
  ```
- `src/Application/Services/Implementation/AuditService.cs:45` :
  `_channel.Writer.TryWrite(trace);` — valeur de retour **ignorée**.
- `src/Application/Services/Implementation/AuditBackgroundService.cs:15` documente
  pourtant le contrat inverse : « PGSSI-S : no trace is lost — the remainder of the
  channel is drained and persisted at shutdown ». Le drainage ne protège que
  l'arrêt, **pas** la contre-pression.

Déclencheur réaliste : la base ralentit (ou une base praticien est injoignable, et
la persistance retombe sur un chemin unitaire, un scope et un aller-retour par
trace). Pendant que le lecteur est bloqué, une synchronisation d'arrière-plan
continue de tracer des milliers de messages. Au-delà de 1000, les plus anciennes
disparaissent.

### Contenu attendu

1. **Couvrir le téléchargement de pièces jointes** : nouveaux types d'action pour
   le téléchargement unitaire et l'export d'archive, tracés comme l'est déjà
   l'export PDF/EML (qui, quoi, quand — **sans** contenu de santé).
2. **Revue de couverture** : passer en revue l'ensemble des sorties de données de
   santé (consultation, export, impression, envoi, téléchargement, recherche ?) et
   documenter dans la task ce qui est tracé et ce qui ne l'est pas
   **intentionnellement**. Le trou actuel vient de l'absence d'inventaire.
3. **Aucune perte silencieuse** : si une trace ne peut pas être mise en file, cela
   ne doit pas être invisible. Options à évaluer et à trancher techniquement
   (attente bornée plutôt que rejet, file plus profonde, `FullMode` bloquant,
   persistance de secours), avec au minimum une **métrique et une alerte** sur
   toute trace perdue. Le principe : la perte doit devenir un signal, pas un
   silence.
4. **Robustesse de la persistance** : le chemin de repli unitaire (un scope et un
   aller-retour par trace) est ce qui provoque l'engorgement — vérifier qu'un
   ralentissement de base ne peut plus vider le journal.
5. **Ne pas régresser sur le contenu** : les traces ne doivent contenir aucune
   donnée de santé en clair (cohérence avec task-184, qui assainit les logs sans
   réduire la couverture d'audit).

### Hors scope

- L'assainissement des logs applicatifs → task-184.
- La refonte du stockage du journal d'audit et sa politique de conservation
  (arbitrage produit distinct).

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test d'intégration : le téléchargement d'une PJ produit une trace d'audit
      (ce test doit échouer sur le code actuel — le vérifier explicitement)
- [ ] Test d'intégration : l'export ZIP de toutes les PJ produit une trace
- [ ] Test unitaire : la trace de téléchargement identifie l'acteur, l'action, la
      ressource et l'horodatage, **sans** contenu de santé ni nom de fichier
      patient-identifiant
- [ ] Test unitaire : quand la file d'audit est saturée, la trace **n'est pas**
      silencieusement perdue — comportement retenu vérifié, et métrique/alerte
      émise dans tous les cas
- [ ] Test unitaire : un ralentissement de la persistance ne provoque pas de perte
      de trace (simulation du chemin de repli unitaire)
- [ ] Inventaire de couverture documenté dans la task : sorties de données de santé
      tracées / non tracées, avec justification pour chaque exclusion
- [ ] Non-régression : les traces existantes (lecture, export PDF/EML, impression,
      envoi) restent produites à l'identique
- [ ] Aucune donnée de santé en clair dans les traces ni dans les logs

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. Ouvrir un message porteur de pièces jointes (données anonymisées) et télécharger
   une PJ, puis « Télécharger tout ».
3. Consulter le journal d'audit (table de traces, ou l'écran d'audit s'il existe) :
   **attendu** — une trace pour chaque téléchargement, avec acteur, action,
   ressource, horodatage. Avant correctif : **aucune** trace, alors qu'un export
   PDF du même message en produit une.
4. Comparer : exporter le même message en PDF → la trace existante est bien là. Les
   deux familles d'action sont désormais symétriques.
5. **Contre-pression** : arrêter le conteneur PostgreSQL (`docker stop`), générer
   un volume de traces important (synchronisation d'une boîte fournie), puis
   redémarrer la base.
   **Attendu** : aucune trace perdue en silence — soit toutes persistées, soit une
   alerte et une métrique explicites indiquant combien ont été perdues et pourquoi.
   Avant correctif : les traces disparaissent sans aucun signal.
6. Vérifier qu'aucune trace ne contient de contenu de message, de nom de fichier
   patient-identifiant, ni d'INS.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : correctif de conformité PGSSI-S § journalisation —
  imputabilité des accès et des sorties de données de santé
- **INS** : ne doit **pas** figurer en clair dans les traces ; l'identification de
  la ressource doit passer par un identifiant technique
- **Authentification PS** : inchangée — l'acteur tracé est l'identité PS
  authentifiée (PSC / e-CPS)
- **Habilitations** : inchangées ; l'accès au journal d'audit doit rester restreint
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : **cœur du sujet**. Évènements à couvrir : téléchargement de
  pièce jointe (unitaire et archive), en plus des consultations, exports,
  impressions et envois déjà tracés. Durée de conservation : celle déjà en vigueur
  dans le repo — à confirmer avec le humain si elle n'est pas explicitement fixée
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : **à mettre à jour** — l'absence de trace sur
  l'exfiltration de pièces jointes empêche de reconstituer les accès en cas
  d'enquête (CNIL ou interne). Signaler au DPO que les périodes antérieures ne sont
  pas reconstituables sur ces deux routes.
