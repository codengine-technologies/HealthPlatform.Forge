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
