# todo-task-178.md — Contenu clinique (CDA, corps MSSanté) envoyé à OpenAI par défaut, hors périmètre HDS

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe confidentialité).
> Finding vérifié sur pièces par le PO — voir « Preuve » ci-dessous.
> **Lié à task-177** : la clé OpenAI committée donne accès à l'historique des
> requêtes de ce compte, donc aux données envoyées ici.

## Objective

Empêcher toute sortie de données de santé du périmètre HDS vers un fournisseur
d'IA tiers **par défaut ou par accident**. Aujourd'hui, le récit clinique des
documents CDA et le corps des messages MSSanté sont envoyés à
`https://api.openai.com/v1` dès que la configuration du fournisseur d'IA n'est pas
exactement `"ollama"` — et c'est le cas en pratique.

Le défaut n'est pas qu'OpenAI soit utilisable : c'est que le **repli silencieux
d'une configuration invalide soit le cloud**, alors que l'intention « IA locale »
n'est portée que par une chaîne de caractères que rien ne valide.

**US backend-only (justification)** : routage et validation de configuration côté
serveur. Aucun contrat ni écran modifié.

### Preuve (état actuel du code)

- `src/Api/Extensions/SemanticKernelExtensions.cs:49-53` — le **cas par défaut
  est le cloud** :
  ```csharp
  return aiProviderOptions.Provider?.ToLower() switch
  {
      "ollama" => services.AddSemanticKernelWithOllama(configuration),
      _        => services.AddSemanticKernelWithOpenAI(configuration)   // <-- défaut
  };
  ```
  Toute valeur absente, mal orthographiée ou inconnue ⇒ OpenAI, sans erreur.
- `src/AppHost/AppHost.cs:102` — la configuration d'amorçage contient une
  **coquille** qui tombe précisément dans ce défaut :
  ```csharp
  .WithEnvironment("AiProvider__Provider", "OpenIA") // Ollama:OpenIA
  ```
  (`OpenIA` ≠ `OpenAI` ≠ `ollama` — aucun des deux cas nommés, donc cloud.)
- `src/Api/appsettings.json:84-85` — `"AiProvider": { "Provider": "OpenAI" }`,
  non surchargé en Production.
- Données réellement transmises :
  `src/Application/Services/Implementation/EmailSummaryService.cs:166-170`
  (récit clinique CDA `doc.Body`, jusqu'à ~15 000 caractères) et
  `src/Application/Consumers/AddNewMailConsumer.cs:189,243`
  (`Subject` + `Body` du message MSSanté, puis corps du document médical).

### Contenu attendu

1. **Aucun repli implicite vers le cloud** : la sélection du fournisseur doit être
   **explicite et validée**. Une valeur inconnue, vide ou mal orthographiée ⇒
   **échec au démarrage** nommant la valeur reçue et les valeurs acceptées, jamais
   un repli. C'est le cœur du correctif.
2. **Corriger la coquille** `"OpenIA"` dans `AppHost.cs` et aligner la valeur avec
   l'intention réelle pour le développement local (voir point 4).
3. **Garde-fou d'environnement** : en environnement **HDS / Production**, un
   fournisseur d'IA externe non couvert par un cadre contractuel validé (HDS ou
   équivalent, et transfert hors UE licite) doit être **refusé au démarrage**.
   L'autorisation doit être un opt-in explicite et traçable en configuration, pas
   un défaut.
4. **Arbitrage humain requis avant implémentation — ouvrir
   `questions/task-178.md`** sur les points que le PO ne peut pas trancher seul :
   - Quel fournisseur d'IA est **autorisé** pour les données de santé en
     Production HDS aujourd'hui (Ollama local ? un hébergeur HDS avec contrat ?
     OpenAI sous DPA/CGU spécifiques ?) ;
   - Existe-t-il un cadre contractuel signé (sous-traitance RGPD art. 28,
     encadrement du transfert hors UE art. 44 et suivants) pour le fournisseur
     actuellement appelé ;
   - Quel est le comportement produit attendu quand aucun fournisseur autorisé
     n'est disponible : fonctionnalités IA **désactivées** (dégradation
     assumée, résumés et tags absents) ou service en erreur ?
   Tant que ces réponses manquent, le correctif se limite au **fail-close**
   (points 1 à 3) : c'est déjà la protection essentielle et elle ne dépend
   d'aucun arbitrage.
5. **Traçabilité** : journaliser au démarrage le fournisseur retenu et son
   endpoint (métadonnée technique, jamais de contenu). Un opérateur doit pouvoir
   répondre en une ligne de log à « où partent les données ? ».
6. **Inventaire des flux sortants** : documenter, dans la doc EPIC, quelles
   données quittent le périmètre pour chaque fonctionnalité IA (résumé, tags,
   chat, recherche sémantique / embeddings) — la base de la mise à jour d'AIPD.

### Hors scope

- Le retrait des secrets committés → **task-177** (à traiter d'abord : la clé
  exposée donne accès à l'historique des requêtes contenant ces données).
- La qualité fonctionnelle des résumés, tags et du chat IA.
- Le choix définitif du fournisseur (arbitrage humain, point 4).
- La migration effective vers un fournisseur HDS (task ultérieure, une fois
  l'arbitrage rendu).

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test unitaire : valeur de fournisseur **inconnue** ⇒ échec explicite au
      démarrage (et **non** un repli vers OpenAI) — ce test doit échouer sur le
      code actuel, le vérifier explicitement
- [ ] Test unitaire : valeur **vide / absente** ⇒ échec explicite au démarrage
- [ ] Test unitaire : `"OpenIA"` (la coquille présente en configuration) ⇒ échec
      explicite, pas un routage cloud silencieux
- [ ] Test unitaire : chaque valeur **valide** route bien vers le fournisseur
      correspondant (dont le fournisseur local)
- [ ] Test unitaire : en environnement Production/HDS, un fournisseur externe non
      autorisé explicitement ⇒ refus au démarrage
- [ ] Coquille `"OpenIA"` corrigée dans `src/AppHost/AppHost.cs`
- [ ] Le fournisseur retenu et son endpoint sont journalisés au démarrage, sans
      aucun contenu de santé
- [ ] Inventaire des flux sortants par fonctionnalité IA documenté (quelle donnée,
      quel endpoint, quel volume maximal)
- [ ] `questions/task-178.md` ouvert avec les 3 arbitrages du point 4 (le
      fail-close est livré indépendamment de leurs réponses)
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

1. **Fail-close sur valeur invalide** : positionner `AiProvider__Provider` sur une
   valeur fantaisiste (`"OpenIA"`, `"gpt"`, vide), lancer
   `cd Api/Mail && dotnet run --project src/AppHost` → **l'application refuse de
   démarrer** avec un message nommant la valeur reçue et les valeurs acceptées.
   Avant correctif, elle démarre et envoie les données cliniques à OpenAI.
2. **Fournisseur local** : positionner le fournisseur sur l'IA locale (Ollama
   disponible), relancer → démarrage OK ; le log de démarrage nomme le
   fournisseur et un endpoint **local**.
3. **Vérification du flux réel** : synchroniser une boîte contenant un message
   avec CDA (données de test anonymisées **uniquement** — ne jamais utiliser de
   données patient réelles pour cette vérification), déclencher le résumé IA, et
   observer le trafic sortant (logs de l'endpoint local, ou capture réseau) :
   **aucune connexion vers `api.openai.com`**.
4. **Garde-fou Production** : simuler l'environnement Production avec un
   fournisseur externe non autorisé → refus au démarrage.
5. Relire les logs : le fournisseur et l'endpoint sont visibles ; aucun sujet,
   corps, ni récit clinique n'apparaît.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — volet MSSanté et documents de santé (CDA)
- **Exigences DSR honorées** : correctif de conformité — confidentialité des DSCP
  et maîtrise des flux sortants hors périmètre HDS (PGSSI-S)
- **INS** : l'INS n'est pas envoyée délibérément, mais le récit clinique CDA et le
  corps des messages **peuvent contenir des identifiants et traits patient** —
  l'inventaire des flux (DOD) doit le qualifier explicitement
- **Authentification PS** : inchangée
- **Habilitations** : non applicable
- **Interop CI-SIS** : le contenu concerné provient de documents **CDA r2**
  (volets CI-SIS) ; le parsing et la validation Schematron via `interop-cda` sont
  inchangés — seule la destination des extraits textuels évolue
- **Tracé PGSSI-S** : journaliser le fournisseur d'IA retenu au démarrage et tout
  refus de démarrage pour fournisseur non autorisé ; **jamais** le contenu envoyé.
  Prévoir la traçabilité des appels sortants (volume, horodatage, fonctionnalité)
  sans contenu
- **Consentement patient** : **à arbitrer avec le DPO** — un traitement par un
  sous-traitant hors UE peut exiger une base légale et une information patient
  spécifiques (question portée dans `questions/task-178.md`)
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui pour `api-mail` — **c'est précisément le problème** :
  le fournisseur d'IA appelé par défaut est hors de ce périmètre et sans
  certification HDS constatée
- **AIPD / impact RGPD** : **à mettre à jour en priorité**. Transfert de données
  de santé vers un sous-traitant hors UE sans base établie (art. 44 et suivants),
  sous-traitance à qualifier (art. 28), et persistance dans les journaux du
  fournisseur. Qualifier la portée réelle avec le DPO : environnements concernés,
  volume de messages traités, période. **Cette qualification est un livrable de la
  task, distinct du correctif technique.**
