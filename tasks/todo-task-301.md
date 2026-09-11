# todo-task-301.md — Dovecot et GreenMail sont démarrés deux fois par exécution : un harnais serveur unique au niveau assembly, et le coût d'entrée d'une suite tombe à zéro

**Repos**: api-mail
**Dependencies**: done-task-300
**Epic**: E016
**Single frontend**: true
**Priorité**: **2** — c'est le **débloqueur** de l'EPIC. Les trois US
suivantes (`297`, `298`, `299`) ajoutent chacune des suites à serveur réel ;
tant que chaque nouvelle collection paie son propre démarrage de conteneurs,
leur coût est prohibitif et elles seront rognées.

> **Origine** : audit de l'exploitation des tests d'intégration api-mail du
> 2026-09-11.

## Objective

Que le serveur IMAP (Dovecot) et le puits SMTP (GreenMail) soient démarrés
**une seule fois par exécution de l'assembly de test**, et qu'une nouvelle
suite à serveur réel puisse s'y brancher en trois lignes — sans re-déclarer un
conteneur, sans re-semer un corpus, sans re-payer un démarrage.

### Ce qui a été mesuré (2026-09-11)

| Grandeur | Valeur mesurée |
|---|---|
| Images déclarées par `ImapServicesFixture` | `dovecot:2.3.21`, `greenmail:2.1.3`, `pgvector:pg16`, `redis:7-alpine` |
| Images déclarées par `UseCaseFixture` | **les mêmes quatre**, re-démarrées |
| Démarrages de conteneur par exécution complète | **8** |
| Coût des collections | `ImapServices` 8,2 s (36 tests) / `UseCases` 44,3 s (55 tests) / smoke de banc 17,5 s (6 tests, **1 conteneur par test**) |
| `APPEND` IMAPS par exécution complète | **~675** (≈ 15 boîtes × 45 messages du corpus) |
| Parallélisme configuré | **aucun** — `xunit.runner.json` : `parallelizeTestCollections: false`, `maxParallelThreads: 1` |
| `AssemblyFixture` (xUnit v3, déjà en place en 4.0.0) | utilisé **nulle part** |

**Mécanique.** Un `ICollectionFixture` vit le temps de **sa** collection. Deux
collections qui veulent un serveur de messagerie déclarent donc deux fois les
mêmes conteneurs, et les démarrent l'un après l'autre puisque le runner est
strictement séquentiel. xUnit v3 — la version déjà utilisée par le projet —
offre `AssemblyFixture`, dont la durée de vie couvre l'assembly entier : c'est
exactement la portée que veut un serveur de messagerie partagé.

**Ce que cela change vraiment.** Le gain de durée est secondaire. Le vrai
effet est que le **coût d'entrée d'une nouvelle suite à serveur réel tombe à
zéro** : aujourd'hui, ouvrir une 3ᵉ collection coûte ~10 s de démarrage plus
un corpus à semer, ce qui condamne toute suite de moins d'une dizaine de
tests. Après, le coût marginal est celui **déjà mesuré** à l'intérieur d'une
collection existante : **0,11 à 0,25 s par test**.

### Contenu attendu

1. **`MailServerFixture` au niveau assembly.** Un `[assembly: AssemblyFixture]`
   porte Dovecot + GreenMail et expose ce que `MailServerTestHarness` sait
   déjà produire (hôte, ports mappés, `DomainSettings`). Les conteneurs
   Postgres et Redis **restent par collection** : ce sont eux qui portent
   l'isolation des bases praticien, et les partager mélangerait les états.
2. **`ImapServicesFixture` et `UseCaseFixture` deviennent consommateurs.**
   Ils ne déclarent plus ni Dovecot ni GreenMail et reçoivent le harnais par
   injection. Aucun test existant ne change de comportement observable.
3. **Table centrale d'allocation des utilisateurs virtuels.** Les indices sont
   aujourd'hui en dur, dispersés dans chaque suite (`2`–`5` pour
   `ImapServices`, `10`–`16`, `40`–`42`, `112` pour `UseCases`) et disjoints
   **par chance**. Avec un Dovecot partagé, une collision devient un
   croisement silencieux de boîtes entre deux suites. Une constante unique
   déclare l'attribution, et un test de garde vérifie qu'aucun indice n'est
   déclaré deux fois.
4. **Registre de boîtes semées partagé et mémoïsé** au niveau du harnais :
   une boîte semée une fois est réutilisée par toute suite qui demande le même
   indice, y compris à travers les collections. Les suites qui **mutent** leur
   boîte (drapeaux, déplacement, envoi) gardent un indice exclusif — invariant
   déjà posé par le harnais actuel, désormais vérifié par la table.
5. **Contrat d'extension publié**, en tête de `MailServerFixture` : ce qu'une
   nouvelle suite doit écrire pour obtenir un serveur réel et une boîte semée.
   C'est le livrable que consomment `297`, `298` et `299`.
6. **Parallélisme des collections activé** : `parallelizeTestCollections: true`
   et `maxParallelThreads: 4`. Le harnais est conçu pour cela (un utilisateur
   virtuel et une base praticien par suite, `mail_max_userip_connections = 100`
   côté Dovecot). À activer **dans cette US et pas avant** : la quarantaine de
   `task-300` doit déjà être en place, sinon le parallélisme sera accusé des
   flakies préexistants.
7. **Mesure avant / après** avec `Tools/timing/measure.sh --kind test`,
   consignée dans le task file. Sans elle, l'optimisation reste un pari —
   c'est la raison d'être de l'instrumentation de la forge.

### Hors périmètre (explicite)

- **Le corpus pré-semé** (volume Maildir monté au lieu de ~675 `APPEND`). Il ne
  devient rentable qu'une fois les suites de `298` et `299` écrites ; il fera
  sa propre task si la mesure le justifie alors.
- Les `*BenchSmokeTests`, qui démarrent volontairement un conteneur jetable
  **par test** : c'est leur objet (ils éprouvent la configuration de banc
  montée depuis `src/AppHost/`), ils ne rejoignent pas le harnais partagé.
- Toute nouvelle capacité serveur (quota, dossiers spéciaux) — objet de
  `todo-task-302`.

## Definition of Done

- [ ] Build passes on api-mail (0 errors)
- [ ] Tests pass (0 failures) hors quarantaine déclarée
- [ ] Un `AssemblyFixture` porte Dovecot et GreenMail ; `grep` sur les images
      `dovecot/` et `greenmail/` ne remonte plus qu'**une** déclaration hors
      `*BenchSmokeTests`
- [ ] Démarrages de conteneur par exécution complète : **de 8 à 6**, constaté
      par observation de `docker ps` ou par les journaux Testcontainers
- [ ] Les 97 tests `Server=real` restent verts, **et le nombre reste 97**
      (aucune suite perdue par un `[Collection]` mal recâblé)
- [ ] Table centrale d'attribution des indices d'utilisateur virtuel + test de
      garde qui échoue si un indice est déclaré deux fois
- [ ] Contrat d'extension écrit en tête de `MailServerFixture` : une nouvelle
      suite obtient serveur + boîte semée sans déclarer de conteneur
- [ ] `xunit.runner.json` : `parallelizeTestCollections: true`,
      `maxParallelThreads: 4`
- [ ] **3 exécutions consécutives vertes** de `Server=real` après activation du
      parallélisme, consignées dans le task file (c'est la seule preuve que
      l'isolation tient)
- [ ] Mesure avant / après consignée : durée totale et durée par collection,
      via `Tools/timing/measure.sh --kind test`
- [ ] Aucune donnée de santé dans le corpus ni les journaux

## Manual Test Plan

- **Avant** : `cd Api/Mail && dotnet test tests/mss.mail.integration.tests --no-build --filter "Server=real"`,
  noter la durée (références mesurées : 74 s à froid, 51 s images tirées) et compter les conteneurs
  `dovecot` / `greenmail` vus par `docker ps` pendant l'exécution
  (référence : 2 de chaque, successivement).
- **Après** : même commande. **Ce que l'humain doit voir** : `réussite : 97,
  échec : 0`, durée attendue ~25 à 40 s, et **un seul** conteneur `dovecot` et
  **un seul** `greenmail` vivants pendant toute l'exécution.
- **Contre-épreuve d'isolation** : relancer la commande **trois fois de suite**
  sans nettoyer. Les trois passes doivent être vertes. Un rouge intermittent
  ici signe une collision d'utilisateur virtuel ou de base praticien — ne pas
  le mettre en quarantaine, c'est un défaut de cette US.
- **Contre-épreuve du test de garde** : dupliquer volontairement un indice
  d'utilisateur virtuel dans la table centrale, constater que le test de garde
  échoue avec un message nommant l'indice, puis revenir en arrière.
- **Données de test** : 100 % synthétiques.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — outillage de vérification interne
- **Exigences DSR honorées** : non applicable — la US porte sur la durée de vie
  des conteneurs de test, pas sur une exigence de référencement
- **INS** : non applicable — corpus synthétique, aucun INS/NIR/NIA
- **Authentification PS** : inchangée. L'authentification IMAP du harnais reste
  la `passdb static` du serveur de test, jamais un secret réel
- **Habilitations** : inchangées — RPPS fictifs (`99700000042` et le RPPS
  distinct du harnais des use cases) conservés
- **Interop CI-SIS** : non applicable directement ; les archives IHE-XDM du
  corpus restent les échantillons CDA synthétiques déjà versionnés
- **Tracé PGSSI-S** : aucun évènement métier nouveau
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — conteneurs locaux, données synthétiques
- **AIPD / impact RGPD** : inchangée
