# todo-task-196.md — Embedding tronqué en caractères et non en tokens : documents cliniques absents de la recherche sémantique, en silence

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : tir de charge 20 utilisateurs du 2026-07-25 sur le banc task-195.
> Défaut **observé en exécution réelle**, pas déduit d'une lecture de code — voir
> « Preuve ».

## Objective

Garantir qu'un document clinique volumineux entre bien dans l'index de recherche
sémantique, au lieu d'en être écarté silencieusement.

Le texte envoyé au service d'embedding est tronqué à un nombre de **caractères**,
alors que le modèle impose une limite en **tokens**. Un compte-rendu CDA réel passe
le garde-fou en caractères tout en dépassant la limite en tokens : le fournisseur
répond `400`, l'exception est attrapée, la méthode retourne `null` — et le document
n'a **aucun vecteur**. Il devient introuvable par la recherche sémantique, sans
aucun signal côté praticien.

Pour un médecin, un compte-rendu qui n'apparaît pas dans une recherche est un
compte-rendu perdu.

**US backend-only (justification)** : indexation côté serveur, aucun contrat ni
écran modifié.

### Preuve (relevé Seq du tir de charge, 2026-07-25 17:20 UTC)

Quatre erreurs pendant un tir de 20 utilisateurs concurrents, sur `medical doc`
**et** sur `email` :

```
EmailEmbeddingService: Failed to generate medical doc embedding
System.ClientModel.ClientResultException: HTTP 400 (invalid_request_error)
  Invalid 'input[0]': maximum input length is 8192 tokens.
    at OpenAI.Embeddings.EmbeddingClient.GenerateEmbeddingsAsync(...)
    at EmailEmbeddingService.GenerateEmbeddingInternalAsync(...) ligne 61
```

Mécanisme, vérifié dans le code :

- `src/Application/Services/Implementation/EmailEmbeddingService.cs:55` — la
  troncature est faite par `TruncateContent(content)`, bornée par un nombre de
  **caractères**.
- Bornes configurées : `src/Api/appsettings.json:94` → **20 000 caractères**
  (OpenAI) ; défaut du code `src/Application/Configuration/OpenAiOptions.cs:19` →
  **30 000**. Côté Ollama : `appsettings.json:102` → 4 000,
  `OllamaOptions.cs:17` → 8 000.
- La limite réelle du modèle est de **8192 tokens**. Le ratio caractères/token
  n'est pas constant : un récit clinique français dense en ponctuation, en nombres
  et en abréviations tokenise beaucoup moins bien qu'un texte courant, si bien que
  20 000 caractères peuvent dépasser 8192 tokens.
- `src/Application/Services/Implementation/EmailEmbeddingService.cs:69-73` —
  l'échec est avalé : `catch (Exception ex)` → `LogError` → **`return null`**.
  L'appelant n'a aucun moyen de distinguer « pas d'embedding » de « embedding
  échoué ».

### Contenu attendu

1. **Borner en tokens, pas en caractères** : la troncature doit s'appuyer sur le
   comptage de tokens du modèle cible (tokenizer, ou API de comptage), avec une
   marge de sécurité. La borne en caractères peut rester en garde-fou grossier de
   premier niveau, mais elle ne peut plus être le seul rempart.
2. **Aligner les bornes par fournisseur** : chaque fournisseur a sa propre limite ;
   les valeurs de configuration et les défauts du code doivent être cohérents avec
   elle et entre eux (aujourd'hui `appsettings.json` et les classes d'options
   divergent : 20 000 vs 30 000, 4 000 vs 8 000).
3. **Repli plutôt qu'abandon** : un dépassement doit conduire à réduire l'entrée et
   réessayer (ou à découper), pas à renoncer au vecteur. Un document **long** doit
   rester trouvable, même si son embedding ne couvre qu'une partie du texte.
4. **Échec visible** : si aucun vecteur ne peut être produit après repli, le
   document doit être **marqué comme non indexé** et l'événement exposé en
   exploitation (métrique / compteur), pas seulement une ligne d'erreur. Le silence
   actuel est le cœur du problème.
5. **Note sur le service de découpage** : `TextChunkingService` existe mais n'a
   **aucun appelant en production** (constaté lors de l'audit du 2026-07-25). Soit
   il est la brique de découpage attendue ici et il faut le brancher, soit il est
   mort et il faut le retirer. À trancher dans la task, pas à laisser en l'état.

### Hors scope

- Le choix du fournisseur d'IA et la sortie de contenu clinique hors périmètre
  HDS → **task-178** (les mêmes traces le confirment en conditions réelles).
- La qualité de la recherche sémantique au-delà de la présence du vecteur.
- Le harnais de tir k6 → task-174.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test unitaire : un contenu **sous** la limite en caractères mais **au-dessus**
      de la limite en tokens produit quand même un vecteur (ce test doit échouer sur
      le code actuel — le vérifier explicitement)
- [ ] Test unitaire : le contenu soumis au fournisseur respecte la limite en tokens
      du modèle cible, marge comprise
- [ ] Test unitaire : sur dépassement, le repli (réduction / découpage) est appliqué
      et un vecteur est produit — pas de `null` silencieux
- [ ] Test unitaire : si aucun vecteur ne peut être produit, le document est marqué
      non indexé et le compteur d'échec est incrémenté
- [ ] Test unitaire de non-régression : un contenu court est embeddé à l'identique
- [ ] Bornes par fournisseur cohérentes entre `appsettings.json` et les classes
      d'options (plus de divergence 20 000/30 000 ni 4 000/8 000)
- [ ] Décision documentée sur `TextChunkingService` (branché ou retiré)
- [ ] Vérification sur le banc : après un tir, **zéro** `Failed to generate … embedding`
      dans Seq sur le corpus `JEUX_TESTS_FULL`
- [ ] Aucune donnée de santé en clair dans les logs (ne pas journaliser le contenu
      tronqué ni le texte soumis — longueurs et compteurs uniquement)

## Manual Test Plan

1. Monter le banc : `MSS_LOADTEST=true dotnet run --project src/AppHost`
   (ou `--launch-profile https-load-test`), Postgres métier joignable.
2. Seeder avec les pièces jointes réelles :
   `dotnet run --project tests/mss.mail.loadtest.seed -- --users 5 --messages 10`
3. Déclencher la pipeline sur une boîte **non encore lue** :
   `POST /api/v1/mail/folders/INBOX/emails/enrich/sync` avec `[1,2,3,4,5]`.
4. Dans Seq, filtrer `Failed to generate` sur la fenêtre du run.
   **Attendu** : aucune occurrence. Avant correctif, plusieurs erreurs
   `maximum input length is 8192 tokens` apparaissent sur les documents longs.
5. Vérifier qu'un **compte-rendu long** (le plus volumineux du corpus) est bien
   retrouvé par une recherche sémantique portant sur un terme figurant dans sa
   partie médiane — c'est le test qui prouve que le document est réellement indexé.
6. Forcer un échec irréductible (borne de tokens abaissée artificiellement) →
   vérifier que le document est marqué non indexé et que le compteur d'échec bouge,
   plutôt qu'un silence.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — volet documents de santé (CDA)
- **Exigences DSR honorées** : correctif de conformité — accès effectif du praticien
  aux documents reçus (un document non indexé est un document introuvable)
- **INS** : non applicable — aucune règle d'identité modifiée
- **Authentification PS** : inchangée
- **Habilitations** : inchangées — l'index reste cloisonné par praticien
- **Interop CI-SIS** : le contenu concerné provient de documents **CDA r2** ;
  parsing et validation Schematron via `interop-cda` inchangés
- **Tracé PGSSI-S** : journaliser l'échec d'indexation d'un document (évènement
  technique + compteur, **sans** contenu ni extrait de texte)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui. **Point de vigilance** : le contenu envoyé au service
  d'embedding sort aujourd'hui du périmètre HDS — c'est le sujet de **task-178**, à
  traiter en amont ou en parallèle. Ce correctif-ci ne doit pas être compris comme
  validant ce flux.
- **AIPD / impact RGPD** : inchangé par ce correctif — mais signaler au DPO que le
  volume de contenu clinique transmis au fournisseur d'embedding **augmentera**
  mécaniquement si un découpage est mis en place (plusieurs appels par document au
  lieu d'un seul tronqué). Arbitrage à articuler avec task-178.
