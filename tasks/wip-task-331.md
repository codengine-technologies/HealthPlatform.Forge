# todo-task-331.md — Un document rattaché à un patient apparaît dans son dossier, et le dossier ne mélange jamais deux identités qui partagent un matricule

**Repos**: api-mail
**Dependencies**: — (aucune ; à coordonner avec task-191, qui traite les **doublons** de fiches pour une même identité)
**Epic**: E009
**Single frontend**: true
**Priorité**: **1** — le rattachement manuel imposé par task-176 est **sans effet visible** : le document sort de la file « à intégrer » sans entrer dans aucun dossier ; et la garde d'opposition peut lire la mauvaise fiche.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-05** — contre-vérifié — et **AUD-34**).

## Ce qui est établi (develop @ `14d58398`)

**Rattachement invisible (AUD-05)** — `PatientRepository.cs:851-866` (`AttachDocumentToPatientAsync`)
ne pose que `doc.PatientId` ; le dossier (`/patients/{patientId}/medical-documents`) résout
l'identifiant en INS (`PatientHandleResolver.cs:37-48`) puis filtre `md.Ins == ins`
(`ActiveDocumentsForPatient`, `:548-564`). Un CDA arrivé **sans INS** (cas nominal depuis task-176)
garde `Ins = null` : il disparaît de la file (qui compte `PatientId == null`) sans entrer dans la
chronologie. Le test existant (`AttachDocumentToPatientAsyncShouldUpdatePatientIdAsync`) ne vérifie que `PatientId`.

**Identités fusionnées (AUD-34)** — task-183 crée deux fiches pour un même matricule dans deux domaines
(NIA/NIR, OID de test et de production). Mais :
- le dossier filtre sur le matricule seul (`PatientRepository.cs:548-552`) → la fiche X affiche aussi les documents de la fiche Y ;
- `GetOppositionAsync` / `UpdateOppositionAsync` (`:644-651`, `:667-671`) font
  `FirstOrDefaultAsync(x => x.Ins == ins)` **sans `ORDER BY`** → fiche arbitraire ;
  `PatientOppositionGuard.cs:55` peut lire la fiche **non opposée** et laisser partir un envoi sans acquittement ;
- `AddPatientMessageDocumentAsync` (`MailRepository.cs:471`) rattache les messages patient par matricule seul, sans l'arbitrage par domaine de task-183.

## Objective

Que le dossier d'un patient soit défini par **l'identité de la fiche** (et non par le matricule seul) :
un document rattaché à la main y apparaît immédiatement, deux identités distinctes partageant un
matricule ne se mélangent jamais, et l'opposition lue et écrite est celle de la fiche visée.

### Périmètre

1. **Dossier clé sur la fiche** : `ActiveDocumentsForPatient` et les requêtes du dossier filtrent par
   `PatientId` (ou par `(Ins, PatientOid)` si `/develop` établit que `PatientId` n'est pas renseigné
   sur tous les documents historiques — dans ce cas, reprise des documents existants documentée).
2. **Rattachement manuel** : le document rattaché apparaît dans le dossier de la fiche ; la file
   « à intégrer » et le dossier restent cohérents (un document est dans l'un ou dans l'autre).
3. **Opposition** : lecture et écriture par identifiant de fiche ; `PatientOppositionGuard` lit la fiche
   du destinataire effectivement visé.
4. **Messages patient** : rattachement avec le même arbitrage par domaine que le chemin CDA (task-183).
5. **Reprise des données** : les documents déjà rattachés à la main (PatientId posé, Ins nul) deviennent
   visibles sans action du praticien.

### Hors périmètre

- La déduplication des fiches d'une même identité (task-191).
- La création de patient depuis le rattachement — **interdite** (garde-fou métier), inchangée.

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Test rouge d'abord** (log du run rouge dans le task file) : CDA sans INS rattaché à la main à la fiche X →
      sur le code actuel **absent** du dossier de X ; après correctif **présent**, et absent de la file « à intégrer »
- [ ] Test : deux fiches même matricule, domaines différents (NIR / NIA) → le dossier de chacune ne montre que ses documents
- [ ] Test : opposition posée sur la fiche Y → la garde lit l'opposition de la fiche **effectivement destinataire**, de façon déterministe
- [ ] Test : message patient Mon Espace Santé rattaché selon l'arbitrage de domaine task-183
- [ ] Test : document historique (PatientId posé, Ins nul) visible après la reprise
- [ ] Test d'intégration endpoint (règle 1b) : `POST /medical-documents/{id}/attach-patient` puis `GET /patients/{patientId}/medical-documents` → le document est présent
- [ ] Migration éventuelle auditée (règle 7c) : fichier lu, aucune opération fantôme, companion présent, aucun écart de modèle
- [ ] Aucune INS, NIR ni trait patient dans les logs

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` ; Blazor ou mobile connecté à une boîte de test.
2. Recevoir un mail de test portant un CDA **sans INS** (corpus du banc) → il apparaît dans « à intégrer ».
3. Le rattacher à un patient existant de test → **Attendu** : il disparaît de « à intégrer » **et apparaît** dans la chronologie du patient. Avant : il n'apparaît nulle part.
4. Préparer (données de test anonymisées) deux fiches de même matricule dans deux domaines ; ouvrir chacune → chacune ne montre que ses propres documents.
5. Poser une opposition sur l'une, tenter un envoi vers le patient correspondant → la demande d'acquittement s'affiche pour la bonne fiche, et seulement pour elle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : identito-vigilance — rattachement d'un document à la bonne identité ; opposition patient respectée (Mon Espace Santé)
- **INS** : **au cœur** — distinction des domaines d'identité (NIR / NIA, OID) conformément au référentiel INS ; aucune fusion de deux identités sur le seul matricule ; statut INS inchangé par la US
- **Authentification PS** : PSC / e-CPS inchangée
- **Habilitations** : inchangées — dossier limité aux patients du praticien
- **Interop CI-SIS** : CDA r2 — identifiant patient et OID de domaine lus depuis le document (chemin `interop-cda` existant)
- **Tracé PGSSI-S** : rattachement manuel tracé (existant) ; lecture et modification d'opposition tracées
- **Consentement patient** : opposition Mon Espace Santé lue sur la fiche du destinataire effectif
- **Référentiels métier** : référentiel INS (OID des domaines NIR / NIA)
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : inchangé — corrige un risque de mélange d'identités, sans traitement nouveau

## Branches
- `api-mail` (pushed) : fix/task-331-dossier-patient-par-fiche — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-331-dossier-patient-par-fiche (depuis `origin/develop` @ `91fb090c`, task-329 mergée)
- `dtos-mss` : aucune branche au `/start`. `/develop` la crée seulement si un contrat change.

## Timings

*(généré par `tools/timing/report.sh --task task-331 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 18 s | — | — | — | — |
| **Total cycle** | | **18 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
