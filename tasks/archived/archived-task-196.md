# todo-task-196.md — Un document clinique trop long disparaît de la recherche sémantique, sans erreur et sans trace

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune. Le défaut est autoporteur et vit dans `api-mail` seul.
**Priorité**: **1** — c'est une **perte de donnée médicale silencieuse** sur le
chemin de recherche. Le praticien ne voit pas un message d'erreur : il voit une
recherche qui ne remonte pas le document, ce qui est indiscernable d'un document
qui n'existe pas. Aucun signal ne l'avertit, aucun signal ne nous avertit.

> **US référencée depuis longtemps, jamais écrite.** `task-174`, `task-195` et
> `docs/epics/E015-Changelogs.md` renvoient à « task-196 » depuis le 2026-07-25,
> mais aucun `todo-task-196.md` n'a jamais existé. Cette US comble ce trou. Le
> défaut a été **révélé** par task-195 (avant elle, la pipeline n'extrayait rien,
> donc il ne pouvait pas se manifester) et **re-constaté** le 2026-08-02.

## Objective

Qu'aucun document clinique ne puisse être absent de l'index sémantique sans
qu'on le sache, et que la troncature respecte la limite réelle du modèle.

## Le défaut — trois défauts empilés, mesurés dans le code

### 1. La troncature compte des caractères, la limite est en tokens

`TruncateContent` fait `content[.._maxCharacters]`. Or la limite de
`text-embedding-3-small` est de **8 192 tokens**. Le rapport entre les deux n'est
pas constant : sur du texte clinique français, un token vaut souvent 3 à 4
caractères, mais les codes métier (CIM-10, LOINC, CCAM), les identifiants, les
résidus de balisage CDA et les accents le font chuter. **Un contenu sous la borne
en caractères peut donc dépasser 8 192 tokens** — et l'appel part en `400`.

### 2. La borne est dupliquée et incohérente

| Où | OpenAI | Ollama |
|---|---|---|
| `appsettings.json` | 20 000 | 4 000 |
| Défaut dans le code (`OpenAiOptions` / `OllamaOptions`) | **30 000** | **8 000** |

Deux jeux de valeurs, un facteur 1,5 à 2 entre eux, et **trois** implémentations
de `TruncateContent` à garder d'accord :
`EmailEmbeddingService`, `BaseEmbeddingProviderService`, `EmailSummaryService`.

### 3. L'échec est avalé — c'est le plus grave

```
catch (Exception ex) { _logger.LogError(...); return null; }
```

Le `null` remonte, l'appelant continue, **le document n'entre jamais dans
l'index** et rien ne conserve la liste de ce qui manque. Il n'y a ni file de
reprise, ni compteur, ni moyen de répondre à « quels documents sont absents de
l'index ? ». Un `LogError` dans Seq n'est pas un mécanisme de rattrapage.

**Mesure du 2026-08-02** (tir 500 praticiens, 3 min, contre-épreuve task-218) :
**50 occurrences** de `Failed to generate {ContentType} embedding` — seule famille
d'erreurs de la fenêtre.

**Conséquence sur nos propres mesures** : la baseline du scénario `search` du banc
est marquée **PROVISOIRE** depuis task-174. Elle mesure un index **incomplet**,
donc elle est flatteuse pour de mauvaises raisons, et elle ne pourra être
re-dérivée qu'après cette US.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer qu'il suffit de baisser la borne en caractères.** Une borne
  basse « assez sûre » (par ex. 8 000) tronquerait inutilement la grande majorité
  des documents, donc **dégraderait la pertinence de recherche** pour éviter un
  cas limite. Le problème est l'**unité de mesure**, pas la valeur.
- **Ne pas présumer qu'un compteur de tokens approximatif suffit.** Si l'estimation
  sous-évalue, on retombe sur le `400`. Choisir soit un tokeniseur réel du modèle,
  soit une marge explicitement justifiée **plus** un repli qui retronque et
  réessaie sur rejet. Écrire lequel et pourquoi.
- **Ne pas présumer que tronquer est toujours la bonne réponse.** Pour un document
  clinique long, couper à 8 192 tokens jette la fin du document — potentiellement
  la conclusion, qui est souvent ce qui porte le sens. Le découpage en segments
  avec plusieurs vecteurs est une alternative. **Trancher explicitement**, et si
  c'est la troncature, dire ce qu'on accepte de perdre.
- **Ne pas présumer que `return null` peut rester.** Même la troncature corrigée,
  un échec restera possible (indisponibilité du fournisseur, quota, document
  aberrant). L'US doit livrer un moyen de **savoir** et de **reprendre**, sinon
  le même défaut silencieux reviendra sous une autre cause.
- **Ne pas présumer que le découpage en caractères est sûr.** `content[..n]` peut
  **couper une paire de substitution UTF-16** et produire une chaîne invalide.
  Marginal en volume, mais gratuit à traiter correctement.

## Contenu attendu

1. **Une seule** implémentation de la borne, partagée par les trois services —
   la duplication est la cause de l'incohérence.
2. Borne exprimée et vérifiée **en tokens**, alignée sur le modèle configuré
   (et non sur une constante en dur), avec les valeurs d'`appsettings` et les
   défauts de code **mis d'accord**.
3. **Décision tranchée et écrite** : troncature bornée en tokens, ou segmentation
   multi-vecteurs. Avec la raison.
4. **Observabilité de ce qui manque** : un document non indexé doit être
   identifiable après coup (compteur + moyen de lister les documents sans
   vecteur), pas seulement produire une ligne de log.
5. **Reprise** : un document non indexé doit pouvoir être ré-indexé sans
   re-télécharger tout le message.
6. Découpage sûr sur les paires de substitution.

## Hors scope

- Le **choix du modèle d'embedding** et sa dimension.
- La **pertinence** de la recherche sémantique (ranking, seuils) — task-196 rend
  l'index complet, elle n'en change pas le classement.
- La re-dérivation de la baseline `search` du banc : elle **dépend** de cette US
  mais se fera dans un tir dédié, pas ici.

## Definition of Done

- [ ] Build passes (0 erreur) et tests verts sur `api-mail`
- [ ] **Une seule** implémentation de la borne — plus aucune duplication de
      `TruncateContent` (garde par test ou par absence du symbole)
- [ ] Test prouvant qu'un contenu **sous** la borne en caractères mais **au-delà**
      de 8 192 tokens est traité **sans rejet** (c'est le cas qui échoue
      aujourd'hui, à constater **RED avant** le correctif)
- [ ] Test sur un contenu contenant une **paire de substitution** en limite de
      coupe : la chaîne produite reste valide
- [ ] Valeurs d'`appsettings.json` et défauts de `OpenAiOptions`/`OllamaOptions`
      **cohérents** — garde par test
- [ ] Un document dont l'embedding échoue est **listable** après coup (test sur le
      compteur ou la requête d'inventaire)
- [ ] Chemin de **ré-indexation** couvert par un test
- [ ] La décision « troncature vs segmentation » est **écrite** dans le
      `## Develop log` avec sa raison et ce qu'elle accepte de perdre
- [ ] Aucune régression sur `GenerateEmbeddingAsync` : les documents courts
      produisent le même vecteur qu'avant

## Manual Test Plan

```bash
cd Api/Mail && dotnet run --project src/AppHost --launch-profile https-load-test
```

**Écran** : la messagerie — ouvrir un message porteur d'un document clinique
**long** (le corpus `Tools/EmailSender.Console/JEUX_TESTS_FULL` en contient ;
prendre le CDA le plus volumineux), le laisser s'enrichir, puis lancer une
recherche sémantique sur une expression figurant **dans la fin** du document.

**Ce que l'humain doit voir** :
- le document **remonte** dans les résultats de recherche — aujourd'hui il est
  absent, et rien ne le signale ;
- aucun `Failed to generate ... embedding` dans Seq sur la fenêtre
  (`@MessageTemplate like '%embedding%'` et `@Level in ['Error','Fatal']`) ;
- ⚠️ **le contrôle qui compte** : si l'on force un échec (couper le fournisseur
  d'embedding le temps d'un enrichissement), le document doit apparaître dans
  l'**inventaire des documents non indexés** — et non disparaître en silence.

**Données de test** : corpus de test synthétique, aucune donnée de santé réelle,
aucun INS réel.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — messagerie MSSanté du praticien.
- **Vague Ségur** : hors vague — complétude de l'index de recherche interne.
- **Exigences DSR honorées** : aucune nouvelle.
- ⚠️ **Le point dur — perte de donnée médicale silencieuse.** Un document
  clinique reçu, stocké, mais **absent de la recherche** est un document que le
  praticien ne retrouvera pas au moment où il en a besoin. Le défaut ne corrompt
  rien et n'affiche rien : il rend le document introuvable par la seule voie qui
  le cherchait. C'est la raison de la priorité 1, et c'est ce que le contrôle
  d'inventaire du Manual Test Plan vérifie.
- **INS** : non manipulée par le chemin d'embedding. ⚠️ Le contenu envoyé au
  fournisseur d'embedding est du **contenu clinique** : la correction ne doit
  **pas** élargir ce qui sort du système. Si le fournisseur est externe, la
  segmentation multiplierait le nombre d'appels **sans** changer le volume de
  contenu exposé — à vérifier, et à ne pas franchir sans arbitrage.
- **Authentification PS** : inchangée. **Habilitations** : inchangées — l'index
  reste cloisonné par praticien, aucune clé ni requête ne change de portée.
- **Tracé PGSSI-S** : l'inventaire des documents non indexés est une donnée
  d'exploitation, pas un évènement métier — il ne doit contenir **ni** contenu
  clinique **ni** INS, seulement des identifiants techniques.
- **Interop CI-SIS** : non applicable — le CDA est déjà parsé en amont, cette US
  ne touche pas l'extraction.
- **Hébergement HDS** : sans changement.
- **AIPD / impact RGPD** : ⚠️ **à confirmer** — si la décision retenue est la
  segmentation, le nombre d'appels au fournisseur d'embedding augmente. Aucune
  donnée nouvelle ne sort, mais la **fréquence** change ; à valider auprès du DPO
  si le fournisseur est externe. Durées de conservation inchangées.

## Branches

- `api-mail` (pushed) : `fix/task-196-embedding-token-truncation` —
  https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-196-embedding-token-truncation
- `dtos-mss` (pushed, auto-inclus) : même nom de branche — aucun changement de
  contrat attendu (US backend pure, `**Single frontend**: true`) ; la branche
  restera probablement sans commit et sans PR.

> **Contexte de démarrage (2026-08-08)** : le défaut est **re-constaté en charge**
> sur le smoke du jour — `ClientResultException` = 1 286 en 20 minutes, avec le
> `HTTP 400 — maximum input length is 8192 tokens` sur pièce
> (`EmailEmbeddingService.GenerateEmbeddingInternalAsync`, praticien
> `loadtest-49`). Cette famille d'exceptions avait été **mal attribuée à
> Flagsmith** dans deux rapports de tir (rectificatif consigné dans
> `Api/Mail/tests/loadtest-k6/reports/INDEX.md`, 2026-08-08) : ce n'est pas du
> bruit d'infrastructure, c'est le compteur des documents cliniques absents de
> l'index sémantique. `FlagsmithAPIError` vaut 0 sur la même fenêtre.
>
> **À mesurer dans la DOD** : la part exacte des `ClientResultException` due au
> dépassement de tokens, distinguée des annulations clientes emballées par le
> même type — comptage par message Seq, pas par famille d'exception.

## Develop log

### Décision 1 — troncature bornée en TOKENS, pas segmentation multi-vecteurs

**Retenu** : une seule borne d'entrée, exprimée dans l'unité du modèle (le token),
appliquée avec le **tokeniseur réel** du modèle configuré.

**Écarté (pour cette US)** : la segmentation en plusieurs vecteurs par document.
Elle préserverait la fin des documents longs, mais elle change le **modèle de
données** (N vecteurs par document) et le **classement** des résultats — or
task-196 place explicitement la pertinence hors périmètre, et sa section
conformité interdit de franchir ce pas « sans arbitrage ». La segmentation reste
une US candidate ; cette US lui fournit précisément le chiffre qui permettra de
l'arbitrer (voir ci-dessous).

**Ce qu'on accepte de perdre, dit franchement** : au-delà de la borne, **la fin
du document n'est pas indexée**. Le document reste intégralement lisible dans le
message — seule la recherche sémantique ignore sa queue. Un document clinique
porte souvent sa conclusion à la fin : c'est un vrai renoncement, pas un détail.
Il est rendu **mesurable** par le drapeau `WasTruncated` du bornage : si les
documents tronqués s'avèrent nombreux, la segmentation devient justifiable sur
mesure au lieu d'être supposée.

### Décision 2 — tokeniseur réel + marge + repli, plutôt qu'une estimation

L'US interdit l'estimation approximative (« si l'estimation sous-évalue, on
retombe sur le 400 »). Trois protections empilées :

1. **Tokeniseur réel** du modèle (`Microsoft.ML.Tokenizers`, vocabulaire
   `cl100k_base` **embarqué en ressource** — aucun téléchargement au démarrage,
   donc compatible d'un déploiement HDS cloisonné) ;
2. **Marge de sécurité de 2 %** (164 tokens sur 8 192) : un fournisseur peut
   compter des tokens de protocole en plus du contenu, et un vocabulaire local
   peut diverger de quelques unités. Coût négligeable sur le document ;
3. **Repli sur rejet** : si l'appel part quand même en dépassement, le contenu
   est re-borné plus bas et l'appel **réessayé une fois**. C'est la bretelle qui
   couvre ce que la ceinture n'avait pas prévu.

### Décision 3 — la coupe se fait sur une frontière de token

Corollaire gratuit : une coupe sur frontière de token ne peut pas scinder une
paire de substitution UTF-16 (le défaut de `content[..n]` en unités de code).
Un filet indépendant du tokeniseur recule d'une unité si l'index tombe malgré
tout entre les deux moitiés d'une paire.

### Dépendance transitive remontée (sécurité)

`Microsoft.ML.Tokenizers` 2.0.0 embarque `Microsoft.Bcl.Memory` **9.0.4**, qui
porte une vulnérabilité de **sévérité haute** (`GHSA-73j8-2gch-69rq`) — le build
du repo la refuse, à raison. La dépendance est **remontée explicitement en
10.0.10** dans `Directory.Packages.props` plutôt que l'alerte contournée.

## Simplify log

Passe qualité `/forge-simplify` du 2026-08-08 — `api-mail` seul repo touché
(`dtos-mss` sans commit : aucun changement de contrat, comme la DOD l'exige).

**Le constat qui domine la passe** : task-196 a été écrite par deux agents
travaillant **en parallèle sans se voir**, et toute la duplication trouvée est
tombée exactement sur leur frontière. C'est un enseignement de méthode, pas un
hasard — la passe qualité est ce qui rattrape le prix de la parallélisation.

| Axe | Constat | Correction |
|---|---|---|
| Réutilisation | `EmailEmbeddingService` et `BaseEmbeddingProviderService` portaient **chacun sa copie** du même chemin d'appel (~35 lignes : activité, logs, appel borné, compteur d'échec et sa branche *cancelled/provider_error*). Une correction sur une seule copie aurait désaligné la sémantique du compteur **en silence**. | Chemin unique `BoundedEmbeddingInvoker.GenerateVectorOrNullAsync` ; les trois libellés qui variaient regroupés dans `EmbeddingCall`. La classe de base ne garde que ce qu'elle ajoute vraiment. |
| Réutilisation | La composition du texte vectorisé était écrite **deux fois** (voie nominale et reprise) — alors que le commentaire de la reprise **exige** que le texte soit le même. Invariant énoncé, rien ne le tenait. | `MedicalDocumentEmbeddingText.Compose` : un seul endroit, avec le pourquoi (un vecteur reconstruit d'un texte composé autrement n'est pas comparable à l'index). |
| Simplification | `ReindexOneAsync` répétait 4 fois le même appel de métrique dont seul le résultat variait. | Local `RecordReindexOutcome(outcome)`. |
| Efficacité | `EmbeddingInputBounder.Bound` tokenisait **deux fois** : comptage complet du document, puis coupe. Sur les documents longs — la raison d'être de ce chemin — la première passe était intégralement jetée. | Passe unique. |
| Altitude | Rien à redire : contrôleur purement délégant, plafond d'inventaire au niveau du dépôt, borne isolée de son montage DI. | Aucune modification. |

**Non retenu, délibérément** : les troncatures en caractères de
`EmailSummaryService`/`EmailTaggingService` (garde-fous de coût sur un modèle de
chat, hors sujet) ; la marge de 2 % et le réessai unique (ceinture et bretelles
voulue) ; l'absence de collaborateur IMAP dans la reprise (garantie
structurelle testée) ; la forme PGSSI-S des modèles d'inventaire (non enrichis
« pour la commodité »).

Build 0 erreur, **3 575 tests verts** avant et après la passe — aucun
comportement changé, aucun rollback nécessaire.

## Sonar log

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | **non mesuré** | **non mesuré** | — |
| New coverage | non mesuré | non mesuré | — |
| Bugs / Vulnérabilités / Smells | non mesuré | non mesuré | — |

**`/sonar` n'a pas pu tourner le 2026-08-08** : serveur SonarQube injoignable
(`http://127.0.0.1:9000/api/system/status` → aucune réponse, aucun conteneur
`sonar` en marche) et `SONAR_TOKEN` absent de l'environnement.

**Ce n'est pas un « rien à signaler ».** Aucune analyse n'a eu lieu : la qualité
de ce diff n'est **ni verte ni rouge, elle est non mesurée**. Confondre les deux
serait exactement l'erreur que cette EPIC s'interdit.

Ce qui est établi sans Sonar, et qui ne le remplace pas : build 0 erreur,
**3 575 tests verts** (54 nouveaux), et la passe `/forge-simplify` ci-dessus.

**À faire avant merge** (relève de l'humain — Sonar est sur son poste) :
démarrer SonarQube, poser `SONAR_TOKEN`, relancer `/sonar 196`. Le diff est
localisé (chemin d'embedding + inventaire), donc l'analyse est rapide.

## Lint log

`/lint-angular` — **skip propre** : `client-angular` n'est pas dans les
`**Repos**:` de cette task (US backend pure, `**Single frontend**: true`).
Aucun code Angular produit, rien à linter.

## Lint mobile log

`/lint-mobile` — **skip propre** : `client-mobile` hors `**Repos**:`, et
`Client/Mobile/` n'est pas un dépôt git sur ce poste.

## Visual verify log

`/verify-visual` — **skip propre** : aucun écran `client-mobile` touché (pas de
`## Stitch design log`, `client-mobile` hors périmètre). Rien à capturer.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/171
  — label `awaiting-human-merge`, ~50 fichiers
- `dtos-mss` : **aucune PR** — branche auto-incluse restée sans commit. Aucun
  changement de contrat, conforme à `**Single frontend**: true`.

## Code Review Summary

Verdict initial : **CHANGES REQUESTED**, puis **APPROVED après correction sur la
branche** (`bb7d988`).

**Les deux défauts bloquants venaient de la même cause de fond** : task-196 a été
écrite par deux agents travaillant **en parallèle sans se voir**, et toute
l'anomalie s'est logée à leur jointure. C'est l'enseignement de méthode du cycle.

1. **Le compteur d'échec comptait double** — chacun des deux agents avait posé
   son incrément, et la passe `/forge-simplify` a mutualisé le chemin d'appel
   **sans retirer** ceux des appelants. Deux conséquences réelles : le compteur
   qui doit répondre à « combien de documents manquent » était **faux et
   incohérent d'une étiquette à l'autre** (`medical_document` doublé,
   `email` juste) ; et à chaque **arrêt propre**, l'annulation classée
   `cancelled` par l'invocateur se doublait d'un `provider_error` de l'appelant
   — toute alerte posée sur cette cause se serait déclenchée. La distinction que
   le code documente comme « ce qui rend le chiffre actionnable » était annulée
   par l'appelant.
   **Le test qui manquait est ajouté** : « un document perdu = **une** mesure,
   avec la bonne cause », sur la voie nominale complète. C'est son absence qui a
   laissé passer la régression.
2. Deux `packages.lock.json` non commités, que tout build régénérait.

**Suggestions également traitées** : marqueur `too long` qui matchait « took too
long » (un timeout) et faisait réessayer sur un chemin déjà en panne ; branche
`ClientResultException` du discriminant exercée par aucun test **alors que c'est
le type constaté en production** ; voie nominale qui pouvait écrire un vecteur
nul par-dessus un index valide, là où la reprise s'en gardait déjà.

**Ce que la revue a vérifié plutôt que supposé** : le tokeniseur éprouvé
empiriquement (l'optimisation en passe unique conserve `TokenCount` juste dans
les deux branches) ; le test de non-fuite d'INS est une vraie preuve (liste
blanche des propriétés **et** balayage des valeurs à la recherche de l'INS et du
corps réellement semés) ; la portée praticien est **structurelle** — aucun
chemin ne permet de lister ou ré-indexer les documents d'un confrère.

**Divergence assumée, à arbitrer au HAG** : le DOD exigeait « plus aucune
duplication de `TruncateContent` ». Deux subsistent (`EmailSummaryService`,
`EmailTaggingService`), délibérément : garde-fous de **coût** sur `gpt-4o-mini`
(contexte 128 k), deux ordres de grandeur sous sa limite — les convertir aurait
aligné l'unité sans rien corriger.

**Dette explicitement notée** : l'inventaire ne couvre que les documents
médicaux (`MailContent.Embedding` peut aussi être nul) ; la ré-indexation en
masse est synchrone dans la requête HTTP ; le prédicat `Embedding IS NULL` est
prouvé contre le fournisseur en mémoire, pas contre pgvector réel.

Build **0 erreur 0 warning**, **3 580 tests verts** (59 nouveaux).

## Merged

- **Date** : 2026-08-08, via `/merge task-196 --i-tested` (attestation humaine HAG)
- **api-mail** : PR #171 squash-mergée → `cbde5ce` sur `develop` ; branche distante supprimée, branche locale conservée.
- **dtos-mss** : aucune PR (branche auto-incluse sans commit) — refs locale et distante supprimées.
- **Staging** : aucune branche `forge/staging-*` — cycle `/start` isolé.
- **⚠️ CE QUI RESTE DÛ, et c'était déjà écrit dans la revue** :
  - `/sonar 196` — la qualité de ce diff est **non mesurée** (serveur injoignable
    pendant tout le cycle), ce qui n'est ni vert ni rouge ;
  - le prédicat `Embedding IS NULL` de l'inventaire est prouvé contre le
    fournisseur **en mémoire**, pas contre pgvector réel (Docker indisponible
    dans la session) ;
  - **conséquence pour le banc** : la baseline du scénario `search`, marquée
    PROVISOIRE depuis task-174 parce qu'elle mesurait un index **incomplet**,
    peut désormais être re-dérivée — mais elle ne l'a pas encore été.
- **Divergence assumée au HAG** : deux `TruncateContent` subsistent
  (`EmailSummaryService`, `EmailTaggingService`) là où le DOD exigeait zéro —
  garde-fous de **coût** sur un modèle de chat, deux ordres de grandeur sous sa
  limite. Les convertir aurait aligné l'unité sans rien corriger.
