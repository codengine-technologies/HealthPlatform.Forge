# todo-task-410 — Le cache patient par INS est cloisonné par boîte

**Repos**: api-mail
**Dependencies**: aucune
**Epic**: E020

> **Origine** : audit du périmètre « boîte déléguée » du 2026-10-30
> (`Docs/audits/2026-10-30-audit-boite-deleguee.md`), constat **C1 (critique)**.
>
> **Single layer** : correctif backend seul, sans effet visible sur les écrans. Les fronts ne
> changent pas.

## Objectif

Une fiche patient n'est jamais servie à une autre boîte que la sienne. Aujourd'hui, le cache Redis
de la résolution d'un patient par INS a pour clé `patient:ins:{hash(INS)}`. Elle ne nomme ni la base
ni la boîte, et le cache est commun à toute la plateforme. Quand un médecin résout un INS, la fiche
d'un autre cabinet (identité, naissance, identifiant technique) peut lui être rendue pendant 5
minutes. Il apprend du même coup que ce patient est suivi ailleurs.

## Règles

1. La clé de cache d'une fiche patient porte la **base de la boîte** (`UserDatabaseName`), comme
   `BaseRepository.UserIdCacheKey`. Une même valeur d'INS dans deux boîtes donne deux clés.
2. L'invalidation à l'écriture d'une fiche vise la clé de **cette** base.
3. **Revue des autres clés** : toute clé de cache Redis construite sans la boîte ni la base est soit
   cloisonnée, soit justifiée par écrit. Une clé de déduplication de tâche, par exemple, ne porte
   aucune donnée. L'audit n'a trouvé que `patient:ins` ; la revue le confirme ou complète la liste.
4. Les entrées déjà en cache sous l'ancienne clé ne sont plus jamais lues : le changement de format
   suffit, et leur TTL de 5 minutes les efface.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures)
- [ ] Unit test : `PatientCacheKey` diffère pour un même INS dans deux bases, et elle ne contient pas
      l'INS en clair
- [ ] Test d'intégration de bout en bout pour `POST /patients/resolve` : deux boîtes A et B, sur deux
      bases, connaissent chacune une fiche différente pour le même INS. A résout l'INS, puis B le
      résout : B lit **sa** fiche (nom et identifiant de B) dans la réponse réelle. Quand B ne
      connaît pas l'INS, B reçoit l'absence de fiche, jamais celle de A. Vu rouge sur le code d'avant
      le correctif (règle 1b).
- [ ] Revue des clés Redis consignée dans le `## Develop log` : chaque gabarit de clé, sa portée
      (boîte, personne, plateforme) et sa justification
- [ ] Aucune donnée de santé en clair dans les logs ni dans les clés Redis (l'INS reste haché)
- [ ] `conventions/csharp.md` : entrée « une clé de cache d'une donnée de boîte nomme la boîte »

## Manual Test Plan

- Backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil e2e).
- Deux médecins du seed, sur deux boîtes, avec chacun un patient de même INS (seed ou fiche saisie).
- Médecin A : ouvrir la fiche du patient par son INS. Médecin B, dans les 5 minutes : rechercher le
  même INS.
- Attendu : B voit sa propre fiche, ou « aucun patient », jamais le nom saisi chez A.
- Redis (`redis-cli --scan --pattern 'patient:ins:*'`) : les clés portent le nom de base.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif de sécurité
- **Exigences DSR honorées** : non applicable — confidentialité des données de santé (PGSSI-S,
  cloisonnement des données entre structures)
- **INS** : manipulée comme clé de recherche. Statut inchangé, jamais en clair dans la clé ni dans
  les logs.
- **Authentification PS** : inchangée (PSC)
- **Habilitations** : une fiche patient n'est lue que par les personnes rattachées à sa boîte
  (règle 14)
- **Interop CI-SIS** : non applicable — aucun échange
- **Tracé PGSSI-S** : inchangé (`PatientRecordViewed`). La journalisation de l'objet consulté relève
  de task-413.
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — Redis et PostgreSQL de la plateforme
- **AIPD / impact RGPD** : à noter — la fuite possible entre cabinets avant correctif est à évaluer
  comme incident potentiel (journal de Redis, durée d'exposition). Inchangé après correctif.
