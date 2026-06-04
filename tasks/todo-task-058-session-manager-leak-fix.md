# todo-task-058-session-manager-leak-fix.md — Durcissement du MailClientSessionManager (fuite de sémaphores + boucle de cleanup résiliente)

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**EpicTitle**: Robustesse & observabilité de la plateforme

## Objective

Corriger deux défauts de stabilité long-running dans
[MailClientSessionManager.cs](Api/Mail/src/Application/Session/MailClientSessionManager.cs)
qui dégradent un pod au fil du temps sans aucune alerte.

### Finding B — Fuite mémoire de `SemaphoreSlim` sur sessions expirées (🔴)

Les sémaphores `_imapFolderLocks` et `_emailFetchLocks`
([L18-19](Api/Mail/src/Application/Session/MailClientSessionManager.cs#L18-L19))
ne sont nettoyés que par `CleanupLocksForSession`, appelé **uniquement** lors
d'une suppression **explicite** de session
([L368](Api/Mail/src/Application/Session/MailClientSessionManager.cs#L368)).

Or `CleanupExpiredSessions`
([L441-453](Api/Mail/src/Application/Session/MailClientSessionManager.cs#L441-L453))
dispose la session et la retire de `_sessions`, **mais n'appelle jamais**
`CleanupLocksForSession`. Pour chaque session qui **expire** (cas le plus
fréquent — déconnexion sans logout explicite), ses entrées dans les deux
`ConcurrentDictionary<string, SemaphoreSlim>` **restent à vie**. Résultat :
fuite mémoire monotone proportionnelle au nombre de couples
(utilisateur × dossier) vus depuis le démarrage du pod, jusqu'à pression
mémoire / OOM.

Cible : `CleanupExpiredSessions` doit, pour chaque session expirée, nettoyer
ses sémaphores associés (folder locks + email-fetch locks) **avant** le
`TryRemove`, en réutilisant la logique de `CleanupLocksForSession`.

> Note : `CleanupLocksForSession` ne nettoie aujourd'hui que `_imapFolderLocks`.
> Il faut s'assurer que `_emailFetchLocks` est **aussi** nettoyé (même clé de
> préfixe de session). À traiter dans le cadre de cette task pour éviter une
> fuite résiduelle symétrique.

### Finding C — Boucle de cleanup tuable définitivement (🟠)

Dans `RunCleanupTaskAsync`
([L416-438](Api/Mail/src/Application/Session/MailClientSessionManager.cs#L416-L438)),
le `try/catch` enveloppe **le `while` entier** et non le corps de boucle. Si
`CleanupExpiredSessions()` lève une exception inattendue (non liée à
l'annulation), le `catch (Exception)` est atteint **hors boucle** → la tâche
périodique s'arrête **pour toute la durée de vie du pod**. Plus aucun nettoyage
de session ni de lock ensuite → accumulation jusqu'à OOM, sans alerte.

Cible : déplacer le `try/catch (Exception)` **à l'intérieur** du `while`
(log + continue, la boucle survit à un échec ponctuel), tout en conservant la
sortie propre sur annulation (`OperationCanceledException` / token annulé).

### Iso-comportement

Aucune logique métier modifiée, aucun endpoint touché, aucun contrat impacté.
Périmètre **purement robustesse interne**, mono-repo `api-mail`, sans impact
frontend ni DTO.

## Gherkin

_Pas de `.feature` (BDD déprécié, cf. CLAUDE.md règle 1). Comportements
couverts par tests unitaires._

## Definition of Done

- [ ] Build passes (`dotnet build HealthPlatform.Api.Mail.sln`, 0 erreurs)
- [ ] Tests pass (`dotnet test HealthPlatform.Api.Mail.sln`, 0 échecs)
- [ ] **Finding B** : `CleanupExpiredSessions` nettoie les sémaphores
      (`_imapFolderLocks` **et** `_emailFetchLocks`) de chaque session expirée
      avant de la retirer de `_sessions`
- [ ] `CleanupLocksForSession` (ou son équivalent factorisé) nettoie **les deux**
      dictionnaires de locks (correction de l'oubli actuel sur `_emailFetchLocks`)
- [ ] Chaque `SemaphoreSlim` retiré est `Dispose()` (pas de double-dispose,
      pas de `Dispose` sur un sémaphore encore détenu)
- [ ] **Finding C** : dans `RunCleanupTaskAsync`, le `try/catch (Exception)`
      est à l'intérieur du `while` ; une exception non-annulation **n'arrête
      pas** la boucle (log + continue + délai avant prochaine itération)
- [ ] La sortie propre sur annulation (token annulé / `OperationCanceledException`)
      reste correcte (pas de log d'erreur bruyant au shutdown)
- [ ] Test unitaire (B) : après expiration d'une session ayant acquis des
      folder/email locks, `CleanupExpiredSessions` retire la session **et** ses
      entrées des deux dictionnaires de locks (vérifier via membres internes
      exposés pour le test, ou compteur dédié)
- [ ] Test unitaire (C) : une exception levée par le corps de boucle (mock /
      session factice qui throw sur `IsExpired`/`Dispose`) **n'interrompt pas**
      la boucle — une itération suivante s'exécute malgré l'échec
- [ ] Aucune régression : suppression explicite de session
      (`CleanupLocksForSession` via le chemin existant) inchangée
      fonctionnellement

## Manual Test Plan

- Lancer le backend via l'AppHost Aspire :
  `cd Api/Mail/src/AppHost && dotnet run` (PostgreSQL, Redis, RabbitMQ démarrés
  par Aspire).
- **Finding B (fuite)** : se connecter avec un compte MSSanté, ouvrir
  plusieurs dossiers IMAP (génère des folder/email locks), puis **laisser la
  session expirer** (ne pas se déconnecter explicitement ; attendre le délai
  d'expiration + un cycle de cleanup, ~1 min). Vérifier dans les logs
  (`[CleanupExpiredSessions]` / `[CleanupLocksForSession]`) que les locks de la
  session expirée sont retirés, et que les gauges/métriques de sessions
  reviennent à 0. La mémoire du process ne doit pas croître de façon monotone
  après plusieurs cycles connexion → expiration.
- **Finding C (résilience boucle)** : confirmer (logs) que la tâche
  `[RunCleanupTaskAsync]` continue de tourner périodiquement après le
  démarrage et n'émet pas d'erreur en fonctionnement nominal. Au shutdown
  (`Ctrl+C` sur l'AppHost), vérifier un log d'annulation propre
  (information, pas erreur).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — robustesse/exploitabilité interne de la
  plateforme, sans impact sur un volet métier Ségur.
- **Vague Ségur** : hors Ségur.
- **Exigences DSR honorées** : non applicable — aucun volet de contenu ou de
  transport modifié.
- **INS** : non applicable — aucune donnée patient manipulée.
- **Authentification PS** : inchangée — gestion de sessions IMAP techniques,
  pipeline d'auth applicatif non touché.
- **Habilitations** : non applicable.
- **Interop CI-SIS** : non applicable — aucun échange CDA/FHIR/HL7v2.
- **Tracé PGSSI-S** : inchangé — aucun évènement métier à journaliser n'est
  ajouté ni retiré.
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui — environnement de production HDS existant,
  périmètre inchangé ; la correction réduit le risque d'épuisement mémoire
  (disponibilité du service).
- **AIPD / impact RGPD** : inchangé — aucun traitement de données de santé
  modifié.

### DOD santé (items applicables)
- [ ] Aucune donnée de santé ni secret n'est exposé dans les logs ajoutés
      (clés de session/lock : ne pas logger mot de passe ni jeton — réutiliser
      les patterns de log existants `Email`_`ClientSessionId`)
