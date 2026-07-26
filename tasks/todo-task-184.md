# todo-task-184.md — INS dans les URL et données patient en clair dans les logs et la télémétrie

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe confidentialité).
> Viole frontalement le garde-fou projet « jamais d'INS, de NIR, de NIA ni de
> contenu CDA/MSSanté en clair dans les logs, les URL ou la télémétrie ».

## Objective

Supprimer les fuites de données de santé et de traits d'identité patient vers les
journaux, la télémétrie et les URL. Quatre familles de fuites documentées, toutes
émises à un niveau qui passe les seuils configurés — elles atterrissent donc
réellement dans Seq et dans l'export OTLP, lisibles par un public bien plus large
que celui habilité aux DSCP.

**US backend-only (justification)** : journalisation et routage côté serveur. Le
point sur l'INS en segment d'URL a un impact de contrat — voir point 1.

### Preuve (état actuel du code)

1. **INS en segment d'URL** — cinq routes prennent l'INS en **chemin** :
   `src/Api/Controllers/V1/PatientsController.cs:25,113,147,163,244`
   (`[HttpGet("ins/{ins}")]`, `ins/{ins}/medical-documents`,
   `ins/{ins}/opposition`, …) et `src/Api/Controllers/V1/BiologyController.cs:42`.
   `src/Api/Middleware/RequestLoggingMiddleware.cs:91` pousse `RequestPath` dans le
   contexte Serilog et ne masque que `token=` en query string : **rien** ne masque
   les segments de chemin. L'INS voyage donc aussi dans les logs d'accès de tout
   reverse-proxy.
2. **INS et traits journalisés explicitement** — `PatientsController` logue
   `ins={Ins}` (`:30,122,152,201,252`), et `:201` logue ensemble `lastName`,
   `firstName`, `birthDate`, `gender` ; `:75` sérialise le filtre entier
   (`{@Filters}`). `BiologyController.cs:47,62` fait de même.
3. **Requête de recherche brute en Error** —
   `src/Application/Services/Implementation/SemanticSearchService.cs:114` :
   `_logger.LogError(ex, "Error performing hybrid search for query: {Query}", query)`.
   Le même fichier est pourtant exemplaire ailleurs (`:53`, `:212` ne loguent que
   `queryLength`), et `SearchController.cs:62` porte le commentaire
   « task-071 — PGSSI-S : never log the raw query (potentially nominative) ». Le
   chemin d'erreur a été oublié. Les requêtes sont bel et bien nominatives : le
   code embarque un `PatientNameExtractor.ExtractPatientFromQuery`.
4. **Diagnostics IA** — `src/Api/Controllers/V1/AiDiagnosticsController.cs:67-68`,
   `:145-146`, `:291` loguent la requête brute **et** le nom et prénom du patient
   auto-détecté (`"🔍 Patient auto-détecté dans la requête: {FirstName} {LastName}"`),
   en `Information`.
5. **Anonymisation contournée** —
   `src/Api/Middleware/UserContextEnricherMiddleware.cs:530-536` et `:553-558` :
   le middleware définit `AnonymiseEmail` et `TruncateSub` et les applique
   partout… sauf dans ses deux chemins de rejet, qui loguent l'adresse MSSanté du
   praticien et son `sub` Keycloak en entier. (PII professionnelle, pas DSCP —
   portée moindre, mais la politique du fichier est contredite.)

### Contenu attendu

1. **INS hors des URL** : les routes concernées ne doivent plus véhiculer l'INS en
   segment de chemin. Deux voies possibles (à trancher dans la task, avec la
   contrainte de compatibilité des trois frontends) : passage en corps de requête
   sur une méthode adaptée, ou substitution par un identifiant technique interne
   non signifiant. **Impact contrat** : la bascule des frontends fera l'objet
   d'une task par frontend ; prévoir une transition et la documenter.
   À défaut de bascule immédiate, le **masquage des segments de chemin** dans la
   journalisation et la télémétrie est le minimum non négociable, et doit être
   livré ici.
2. **Journalisation assainie** : ni INS, ni nom, prénom, date de naissance, sexe,
   ni requête de recherche brute, ni contenu de message ou de document. Remplacer
   par des grandeurs non identifiantes (longueurs, compteurs, identifiants
   techniques) — le fichier `SemanticSearchService` montre déjà le bon patron.
3. **Règle homogène** : appliquer l'anonymisation existante (`AnonymiseEmail`,
   `TruncateSub`) sur **tous** les chemins du middleware, y compris les rejets.
4. **Garde-fou anti-récidive** : un contrôle mécanique (analyseur, test, revue
   outillée) empêchant de journaliser un champ marqué sensible. La récidive est
   avérée : task-071 avait déjà durci ce point sur le chemin nominal, et le chemin
   d'erreur juste à côté est passé au travers.

### Hors scope

- Le contenu clinique envoyé au fournisseur d'IA → task-178.
- Les DSCP écrites sur disque → task-185.
- La complétude du journal d'audit → task-186.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test : aucun log émis par les chemins listés ne contient d'INS, de nom, de
      prénom, de date de naissance ni de requête brute (tests sur les cinq
      emplacements identifiés — ils doivent échouer sur le code actuel)
- [ ] Test : le chemin d'**erreur** de la recherche sémantique ne logue que des
      grandeurs non identifiantes (le cas précis oublié par task-071)
- [ ] Test : `RequestPath` journalisé et exporté en télémétrie est **masqué** sur
      les routes portant une INS
- [ ] Test : les deux chemins de rejet du middleware appliquent bien
      `AnonymiseEmail` / `TruncateSub`
- [ ] Garde-fou anti-récidive en place et **prouvé** par un cas de test (une
      tentative de journalisation d'un champ sensible est détectée)
- [ ] Décision documentée sur la sortie de l'INS des URL (voie retenue, calendrier,
      impact des trois frontends) ; masquage livré dans tous les cas
- [ ] Vérification de bout en bout dans Seq : aucune donnée identifiante sur un
      parcours patient complet

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. Ouvrir Seq et filtrer sur `mss.mail`.
3. Parcours patient (données de test anonymisées) : ouvrir un dossier patient,
   lister ses documents médicaux, poser une opposition MSS, consulter un résultat
   de biologie.
4. **Attendu dans Seq** : aucune ligne ne contient l'INS, ni le nom/prénom/date de
   naissance. Avant correctif, l'INS apparaît à la fois dans les messages et dans
   `RequestPath`.
5. **Recherche** : lancer une recherche nominative (« résultats Dupont »), puis
   provoquer un échec de recherche (arrêter le service de recherche vectorielle) →
   la ligne d'erreur ne contient **pas** la requête. Avant correctif, elle la
   contient intégralement.
6. **Diagnostics IA** : appeler un endpoint de diagnostic avec une requête
   contenant un nom de patient → ni la requête ni le nom détecté n'apparaissent.
7. **Rejet d'identité** : forger un jeton sans le claim `mssEmail` → la ligne de
   rejet montre une adresse **anonymisée** et un `sub` tronqué.
8. Vérifier le même résultat côté export OTLP (backend de télémétrie).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : correctif de conformité PGSSI-S — confidentialité
  et journalisation (une trace ne doit jamais elle-même exposer la donnée)
- **INS** : **cœur du sujet** — l'INS ne doit apparaître ni dans les logs, ni dans
  la télémétrie, ni dans une URL (les URL sont journalisées par toute
  l'infrastructure traversée)
- **Authentification PS** : inchangée
- **Habilitations** : la population habilitée à lire Seq et la télémétrie est plus
  large que celle habilitée aux DSCP — c'est précisément ce qui qualifie la fuite
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : les évènements restent journalisés — c'est leur **contenu**
  qui est assaini. Ne pas réduire la couverture du journal en corrigeant (voir
  task-186 qui l'étend)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — vérifier que Seq et le backend de télémétrie sont
  eux-mêmes dans un périmètre conforme ; si non, la fuite est aggravée (à
  confirmer avec le humain)
- **AIPD / impact RGPD** : **à mettre à jour** — divulgation de données de santé
  et de traits d'identité à une population non habilitée. Qualifier la portée avec
  le DPO (rétention Seq, accès, période) et statuer sur la purge des journaux
  existants.
