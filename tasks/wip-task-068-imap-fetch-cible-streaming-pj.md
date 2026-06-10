# todo-task-068.md — Perf IMAP : fetch ciblé des messages et streaming des pièces jointes

**Repos**: api-mail
**Dependencies**: (aucune)
**Epic**: E011
**EpicTitle**: Performance API Mail

> US mono-repo justifiée : optimisation backend pure (granularité des fetchs IMAP
> et streaming HTTP). Aucun changement de contrat DTO ni d'écran frontend — les
> endpoints conservent leurs routes et leurs schémas de réponse.

## Objective

Supprimer le téléchargement systématique du message IMAP **entier** (body +
toutes les pièces jointes décodées en mémoire) là où seuls des en-têtes ou une
seule body part sont nécessaires, et streamer les pièces jointes vers le client
au lieu de les bufferiser en `byte[]`. C'est le finding performance le plus
critique de l'audit : un mail de 50 Mo est aujourd'hui intégralement téléchargé
et décodé pour un simple affichage de contenu, avec risque d'OOM sous requêtes
parallèles.

## Findings adressés (audit perf 2026-06-10)

| # | Localisation | Problème | Impact |
|---|---|---|---|
| 1 | `src/Application/Services/Implementation/ImapService.cs:1525` | `GetMessageAsync` télécharge le message entier pour afficher le contenu | Critique |
| 2 | `src/Application/Services/Implementation/ImapService.cs:1583` | `GetAttachmentAsync` télécharge le message entier pour extraire UNE pièce jointe | Élevé |
| 3 | `src/Application/Services/Implementation/ImapService.cs:1599-1606` | Pièce jointe bufferisée en `MemoryStream` puis `ToArray()` dans un DTO JSON (double/triple copie, OOM possible) | Élevé |
| 4 | `src/Application/Services/Implementation/ImapService.cs:2020-2024` | Copy/Move : boucle `GetMessageAsync` un-par-un (N téléchargements complets séquentiels) | Élevé |
| 5 | `src/Application/Services/Implementation/BackgroundImapService.cs:447-449` | Décodage body part : `MemoryStream` + `ToArray()` + `GetString` = 3 allocations | Moyen |
| 6 | `src/Application/Helpers/EmailAddressHelper.cs:111` | Même pattern triple allocation au décodage MIME | Moyen |

## Comportement attendu

- L'affichage du contenu d'un mail ne récupère que les body parts nécessaires
  (`FetchAsync` avec `MessageSummaryItems` ciblés + `GetBodyPartAsync`), jamais
  les pièces jointes non demandées.
- Le téléchargement d'une pièce jointe ne récupère que la body part visée et la
  **streame** vers la réponse HTTP (pas de `byte[]` intermédiaire complet, pas
  de base64 dans un JSON pour les gros contenus).
- Les opérations copy/move n'effectuent plus N téléchargements complets
  séquentiels (utiliser les commandes IMAP COPY/MOVE serveur quand disponibles,
  sinon batcher).
- Les décodages MIME internes n'allouent plus de copies intermédiaires
  évitables.

## Definition of Done

- [ ] Build passes : `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` (0 erreur)
- [ ] Tests pass : `dotnet test HealthPlatform.Api.Mail.sln` (0 échec)
- [ ] Plus aucun appel `GetMessageAsync` sur le chemin « afficher le contenu d'un mail » (fetch ciblé envelope/body structure + body part)
- [ ] Le téléchargement d'une pièce jointe récupère uniquement la body part demandée via `GetBodyPartAsync`
- [ ] La pièce jointe est streamée vers la réponse HTTP (aucun `MemoryStream.ToArray()` du contenu complet sur ce chemin)
- [ ] Copy/Move : plus de boucle `GetMessageAsync` un-par-un
- [ ] Les 3 sites de triple allocation (`ToArray()` + `GetString`) sont corrigés
- [ ] Unit tests : >= 1 test par méthode publique modifiée d'`ImapService` (mocks MailKit via wrappers existants)
- [ ] Integration test : endpoint de téléchargement de pièce jointe (happy path + pièce jointe introuvable) traverse le pipeline DI complet
- [ ] Aucune régression de contrat : les DTOs exposés et les routes existantes sont inchangés
- [ ] Aucune donnée de santé en clair dans les logs (pas de contenu MIME, pas de nom de fichier patient loggé en clair)

## Manual Test Plan

- Lancer l'API : `cd Api/Mail && docker-compose up -d && dotnet run --project src/Api`
- Ouvrir le client Blazor (`cd Client/Blazor && dotnet run`) connecté à un
  compte de test disposant d'un mail avec une pièce jointe volumineuse (>= 20 Mo,
  donnée de test anonymisée).
- Ouvrir le mail : le contenu s'affiche sans télécharger la pièce jointe
  (vérifier dans les logs serveur que seule la body part texte/HTML est fetchée).
- Télécharger la pièce jointe : le téléchargement démarre immédiatement
  (streaming) et le fichier reçu est intègre (taille + ouverture OK).
- Déplacer 20 mails d'un dossier à l'autre : l'opération aboutit en quelques
  secondes, sans pic mémoire (observer le working set du process).
- Comparer avant/après : temps d'ouverture d'un mail volumineux et mémoire
  consommée doivent baisser visiblement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (LPS MSSanté)
- **Vague Ségur** : hors Ségur — optimisation technique sans impact fonctionnel ni exigence DSR nouvelle
- **Exigences DSR honorées** : non applicable — aucun changement de comportement métier MSSanté
- **INS** : non applicable — aucun traitement d'identité patient modifié
- **Authentification PS** : inchangée (PSC/Keycloak existant) — la US ne touche pas à l'authentification
- **Habilitations** : non applicable — pas de changement d'autorisation
- **Interop CI-SIS** : non applicable — le parsing CDA n'est pas modifié ; les pièces jointes restent transmises octet-à-octet identiques
- **Tracé PGSSI-S** : inchangé — les évènements de consultation/téléchargement existants restent journalisés à l'identique
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement HDS existant inchangé
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement de données

## Branches
- `api-mail` (pushed) : feat/task-068-imap-fetch-cible-streaming-pj — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-068-imap-fetch-cible-streaming-pj
- `dtos-mss` (pushed, auto-included) : feat/task-068-imap-fetch-cible-streaming-pj — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-068-imap-fetch-cible-streaming-pj
