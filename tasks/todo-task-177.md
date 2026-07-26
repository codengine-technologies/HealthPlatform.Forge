# todo-task-177.md — Secrets vivants committés dans `AppHost.cs` (clé OpenAI, clé passerelle FHIR ANS, mots de passe)

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe confidentialité).
> **⚠️ Incident de sécurité — traiter en priorité absolue, avant toute autre task
> de ce lot.** Une partie du traitement est **humaine et hors code** (rotation,
> réécriture d'historique) : voir la répartition ci-dessous.

## Objective

Sortir du code source les secrets aujourd'hui **committés en clair** dans
`src/AppHost/AppHost.cs`, et déclencher la rotation des credentials exposés. Le
fichier porte notamment une clé d'API OpenAI de projet, la clé d'accès à la
**passerelle FHIR de l'ANS** (`gateway.api.esante.gouv.fr`), la clé
d'environnement Flagsmith et des mots de passe de base.

Le dispositif d'externalisation **existe déjà et fonctionne** : un `.env`
correctement git-ignoré porte précisément ces clés, et des commentaires du fichier
indiquent explicitement `=> .env`. Le code les court-circuite en dur.

**US backend-only (justification)** : configuration et amorçage local de
`api-mail`. Aucun contrat ni écran impacté.

### Preuve (constat vérifié, sans divulgation)

Vérifié par le PO **sans jamais afficher les valeurs** :

- `src/AppHost/AppHost.cs` est un fichier **suivi par git** (`git ls-files`).
- Il contient **un** littéral de forme clé de projet OpenAI (`sk-proj-…`),
  **délibérément scindé en deux littéraux concaténés** — ce qui le fait passer
  sous le radar d'un scan de secrets naïf.
- Ce littéral est présent **dans `HEAD`** et dans **3 commits** de l'historique
  (`git log -S`), donc dans tout clone, fork, cache CI et artefact de build.
- 5 affectations de variables d'environnement sensibles dans ce fichier :
  `OpenAi__ApiKey`, `FhirOptions__ApiKey`, `FLAGSMITH_ENVIRONMENT_KEY`, mots de
  passe Postgres et Flagsmith (ce dernier également dans
  `src/AppHost/FlagsmithSeeder.cs`).

Portée aggravante : la clé OpenAI donne accès à l'**historique des requêtes** du
compte, lequel contient des prompts cliniques (voir task-178).

Hors périmètre du finding : `src/Api/appsettings.Development.json` porte la même
valeur mais est git-ignoré et absent de l'historique — local uniquement.

### Répartition du traitement

**Partie humaine — à faire immédiatement, hors forge (non automatisable) :**

1. **Rotation** de tous les credentials exposés : clé OpenAI, clé passerelle FHIR
   ANS (procédure ANS), clé d'environnement Flagsmith, mots de passe Postgres et
   Flagsmith. La rotation prime sur le nettoyage du code : tant que la clé est
   valide, le retrait du littéral ne protège rien.
2. **Décision sur l'historique git** : la réécriture d'historique
   (`git filter-repo` ou équivalent) est nécessaire pour effacer la valeur des
   3 commits, avec la coordination que cela impose sur un repo partagé. À arbitrer
   par le humain — la forge ne réécrit jamais l'historique.
3. **Revue d'accès** : qui a eu accès au repo, aux forks, aux caches CI, aux
   artefacts de build sur la période. Statuer avec le DPO sur la qualification
   RGPD (voir section conformité).

**Partie code — périmètre de cette task :**

1. **Aucun secret littéral** dans `src/AppHost/AppHost.cs`, `FlagsmithSeeder.cs`
   ni ailleurs dans le code suivi : lecture **exclusive** depuis la configuration
   (`.env`, variables d'environnement, gestionnaire de secrets).
2. **Fail-fast au démarrage** : un secret requis absent ⇒ message d'erreur
   explicite nommant la clé manquante et **arrêt**. Jamais de repli silencieux,
   jamais de valeur par défaut de secours.
3. **Aucune valeur de secret journalisée** ni affichée au démarrage. Attention au
   piège connu du workspace : `${VAR:+<set>}${VAR:-<missing>}` en bash **imprime
   le secret** — utiliser `[ -n "$VAR" ] && echo "<set>" || echo "<missing>"`.
4. **Garde-fou anti-récidive** : un contrôle mécanique refusant l'introduction
   d'un littéral de forme secret dans le code suivi (hook, règle CI ou test),
   capable de détecter le contournement **par concaténation** utilisé ici.
5. **Documentation** : `.env.example` (sans valeurs) listant toutes les clés
   requises, et la procédure de démarrage local mise à jour.

### Hors scope

- La rotation elle-même et la réécriture d'historique (humain, ci-dessus).
- La question du routage des données cliniques vers OpenAI → **task-178**.
- L'audit des secrets des autres repos du workspace (un secret Gmail committé est
  connu ailleurs et n'a **pas** été retrouvé dans `api-mail`).

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] `git grep` sur le code **suivi** ne remonte plus aucun littéral de forme
      secret (clé OpenAI, clé FHIR, clé Flagsmith, mot de passe) — y compris
      recherche **résistante à la concaténation** de littéraux
- [ ] Toutes les valeurs sensibles proviennent de la configuration ; aucune valeur
      par défaut en dur, aucun repli silencieux
- [ ] Démarrage sans secret requis ⇒ échec immédiat et message nommant la clé
      manquante (test automatisé sur ce comportement)
- [ ] Aucun secret dans les logs de démarrage, ni en clair ni partiellement
      (test ou vérification documentée)
- [ ] Garde-fou anti-récidive en place et **prouvé** : un littéral de test
      scindé en deux morceaux concaténés est bien détecté
- [ ] `.env.example` complet (clés, aucune valeur) + procédure de démarrage local
      à jour
- [ ] Démarrage local vérifié de bout en bout avec les secrets en `.env`
- [ ] Note d'incident rédigée pour le humain : credentials exposés, fenêtre
      d'exposition, état de la rotation, décision sur l'historique git

## Manual Test Plan

1. Renseigner les clés (après rotation) dans le `.env` du workspace.
2. Lancer : `cd Api/Mail && dotnet run --project src/AppHost` → l'application
   démarre, IA et passerelle FHIR fonctionnelles comme avant.
3. **Retirer** une clé requise du `.env`, relancer → échec immédiat au démarrage
   avec un message nommant la clé manquante (et non un 500 tardif à la première
   requête IA).
4. Relire les logs de démarrage : aucune valeur de secret, même tronquée.
5. Vérifier le nettoyage : `git grep -i 'sk-proj'` (et équivalents) sur les
   fichiers suivis ne remonte rien.
6. Tester le garde-fou : introduire dans un fichier suivi un faux secret **scindé
   en deux littéraux concaténés**, tenter le commit → refus explicite. Retirer.
7. Vérifier avec le humain que la rotation est effective : l'ancienne clé OpenAI
   est révoquée (un appel avec l'ancienne valeur échoue).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — le credential exposé donne accès à une passerelle
  **nationale** (FHIR ANS)
- **Exigences DSR honorées** : correctif de conformité PGSSI-S — gestion des
  secrets et protection des accès aux téléservices ANS
- **INS** : non applicable directement — mais l'accès au compte OpenAI exposé
  permet de lire un historique de requêtes contenant des données de santé
  (task-178), ce qui étend la portée de l'incident
- **Authentification PS** : inchangée — les secrets concernés sont des
  credentials **applicatifs**, pas l'authentification des praticiens
- **Habilitations** : non applicable
- **Interop CI-SIS** : la clé de la passerelle FHIR ANS relève des volets de
  transport CI-SIS ; sa compromission est à signaler à l'ANS selon leur procédure
  (arbitrage humain)
- **Tracé PGSSI-S** : journaliser l'échec de démarrage pour secret manquant
  (évènement technique, jamais la valeur)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — `api-mail` est hébergé HDS ; un secret dans le code
  source est hors du périmètre de protection HDS
- **AIPD / impact RGPD** : **à mettre à jour**. Violation de l'art. 32 (sécurité
  du traitement). Combinée à task-178, l'exposition peut donner accès à des
  données de santé : à qualifier avec le DPO, y compris sur l'obligation de
  notification CNIL. **Qualification = livrable humain de cette task.**
