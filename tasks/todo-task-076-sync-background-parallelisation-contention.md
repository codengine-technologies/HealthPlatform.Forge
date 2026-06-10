# todo-task-076.md — Perf sync background : parallélisation, réutilisation des connexions IMAP et contention

**Repos**: api-mail
**Dependencies**: todo-task-075 (file de background gérée et propagation des tokens — à implémenter d'abord pour éviter les conflits sur les mêmes fichiers)
**Epic**: E011

> US mono-repo justifiée : optimisation du moteur de synchronisation IMAP
> background. Aucun changement de contrat ni d'UI.

## Objective

Accélérer massivement la synchronisation des boîtes MSSanté et réduire la
contention sous charge : l'enrichissement des mails est aujourd'hui strictement
séquentiel (1000 mails ≈ 1000 allers-retours en série), la connexion IMAP
background est détruite et recréée à chaque cycle (handshake + auth complets),
et l'accès aux sessions IMAP est sérialisé par un sémaphore binaire global.

## Findings adressés (audit perf 2026-06-10)

| # | Localisation | Problème | Impact |
|---|---|---|---|
| 1 | `src/Application/Services/Implementation/BackgroundImapService.cs:193-202` | Enrichissement séquentiel mail par mail (`foreach` + `await`) | Élevé |
| 2 | `src/Application/Services/Implementation/BackgroundImapService.cs:230-233` | Suppression des UIDs un par un → N allers-retours DB au lieu d'un delete batch | Moyen |
| 3 | `src/Application/Services/Implementation/BackgroundImapService.cs:326` | `_imapClient?.Dispose(); _imapClient = new ImapClient();` — reconnexion complète à chaque sync au lieu de réutiliser la session | Élevé |
| 4 | `src/Application/Services/Implementation/ImapConnectionService.cs:198` | `ConnectAsync` + `AuthenticateAsync` par requête au lieu de passer par le pool de sessions (`MailClientSessionManager`) | Élevé |
| 5 | `src/Application/Session/MailClientSessionManager.cs:57-77` | `SemaphoreSlim(1,1)` global : toutes les acquisitions de session IMAP sérialisées | Moyen-Élevé |
| 6 | `src/Application/Services/Implementation/BackgroundSyncService.cs:310-346` | Batches de sync traités séquentiellement, sans concurrence bornée | Moyen |
| 7 | `src/Application/Services/Implementation/Sse*Broker.cs` (3 brokers) | `lock` + `ToArray()` sur la liste des souscriptions à chaque publication | Moyen |
| 8 | `src/Application/Services/Implementation/BackgroundSyncService.cs:343` | Notifications de progression émises à chaque batch sans throttling (backpressure) | Moyen |

## Comportement attendu

- Enrichissement des mails parallélisé avec concurrence bornée
  (`Parallel.ForEachAsync` / batchs `Task.WhenAll`, degré configurable,
  en respectant les contraintes de MailKit : 1 commande à la fois par
  connexion IMAP → paralléliser côté DB/traitement, pas côté folder IMAP).
- Suppressions de mails par lot (une requête pour N UIDs).
- La connexion IMAP background est réutilisée entre cycles (keep-alive NOOP),
  reconnexion uniquement sur défaillance.
- Le chemin requête utilisateur réutilise systématiquement le pool de sessions.
- Verrouillage du gestionnaire de sessions à granularité par session
  (plus de sémaphore binaire global).
- Notifications de progression throttlées (ex. au plus 1/seconde par
  utilisateur).

## Definition of Done

- [ ] Build passes : `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` (0 erreur)
- [ ] Tests pass : `dotnet test HealthPlatform.Api.Mail.sln` (0 échec)
- [ ] Enrichissement parallélisé avec degré de concurrence borné et configurable
- [ ] Delete batch des UIDs manquants (1 requête pour N UIDs, test le prouvant)
- [ ] Plus de dispose/new systématique de la connexion IMAP background entre cycles
- [ ] `ImapConnectionService` passe par le pool de sessions
- [ ] Verrou global du `MailClientSessionManager` remplacé par un verrouillage par session
- [ ] Notifications de progression throttlées
- [ ] Unit tests : >= 1 test par comportement modifié (parallélisme borné respecté, throttling, réutilisation de session via wrappers mockés)
- [ ] Integration test : cycle de sync complet sur un dossier mocké (happy path + interruption en cours de sync)
- [ ] Le résultat fonctionnel de la sync est identique : mêmes mails, mêmes états lus/non lus, mêmes notifications finales
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

- Lancer l'API : `cd Api/Mail && docker-compose up -d && dotnet run --project src/Api`
- Sur un compte de test avec >= 500 mails (données anonymisées), lancer une
  synchronisation initiale complète ; chronométrer et comparer au temps
  pré-US (gain attendu significatif, à consigner dans la PR).
- Pendant la sync, utiliser l'application (ouvrir des mails, naviguer) :
  l'UI reste réactive (plus de sérialisation globale des sessions).
- Laisser l'application inactive 30 minutes puis relancer une action : pas de
  reconnexion complète visible dans les logs (keep-alive efficace).
- Vérifier que la progression s'affiche de façon fluide côté client (throttling
  ne casse pas l'affichage).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (LPS MSSanté)
- **Vague Ségur** : hors Ségur — optimisation technique
- **Exigences DSR honorées** : non applicable — le comportement MSSanté (relève, états) est inchangé
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement HDS existant inchangé
- **AIPD / impact RGPD** : inchangé
