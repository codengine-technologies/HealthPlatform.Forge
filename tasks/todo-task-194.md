# todo-task-194.md — Le chemin IMAP balaye encore toute la table des mails ; historique patient non paginé

**Repos**: api-mail
**Dependencies**: — (aucune dépendance de livraison). **task-267** (corpus de
banc porteur de fils) est un **préalable de mesure**, pas de code : sans elle le
gain reste réel mais non chiffrable — voir le point 4.
**Epic**: E011
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe accès données).
> Rattaché à **E011 (performance api-mail)** et non à E009 : le défaut est de nature
> performance, pas fonctionnelle.

> ### ⚠️ Révision du 2026-08-20 — la moitié de cette task est déjà faite
>
> Relecture demandée par l'humain (« comment es-tu certain de ne pas provoquer de
> régression ? un fil peut être sur une page plus éloignée »). Trois constats qui
> changent le périmètre :
>
> 1. **`task-247` (PR #178) a déjà borné le comptage**, sur le chemin
>    `GetMailsByUidsAsync` (lecture servie par la base) : trois requêtes bornées
>    par la page au lieu de deux balayages. `task-256` l'a affinée. Les numéros de
>    ligne cités plus bas datent d'avant.
> 2. **Le « doublon `:1167-1176` » n'est pas un doublon à corriger — c'est la
>    version corrigée.** Et le `dynamic` a déjà disparu de ce chemin :
>    `BuildThreadCountsByRoot` prend un `IReadOnlyCollection<ThreadLink>`, type
>    nommé, avec le commentaire qui explique pourquoi.
> 3. **Ce qui reste** : `GetThreadCountsAsync` (`MailRepository.cs:4039`), appelé
>    par `OnlineMailDataProvider` — le chemin **IMAP**. Lui balaie toujours la
>    table, et c'est le seul des deux que le banc k6 exerce.
>
> Le travail restant est donc : **porter le remède de task-247 sur le chemin
> IMAP**, en préservant la sémantique de comptage de ce chemin (cf. « La
> sémantique à préserver »).

## Objective

Supprimer deux motifs d'accès aux données dont le coût croît avec la **taille totale
de la boîte** au lieu de la taille de ce qui est demandé. Sur une boîte MSSanté
réelle, la messagerie devient lente au point d'être inutilisable, et la
consommation mémoire du serveur suit le volume de la boîte, non celui de la page.

**US backend-only (justification)** : requêtes côté serveur, aucun contrat modifié.

### Preuve (état actuel du code)

**1. Comptage de fils de discussion — deux balayages complets par page**
`src/Infrastructure/Repository/MailRepository.cs:3171-3181` (et le doublon
`:1167-1176`) émet deux chargements **sans aucun filtre** : tous les `MessageId` de
la base, puis toutes les lignes `(MessageId, InReplyTo, References)` dont l'un des
champs de référence est non vide — sans filtre de dossier, sans pagination, sans
`AsNoTracking`. Il imbrique ensuite
`allMailsWithReferences.Count(m => … m.References.Contains(rootId))` dans une boucle
sur les racines de la page. Le helper `BuildThreadCountsByRoot` (`:1199`) prend un
`IReadOnlyCollection<dynamic>` : **chaque** accès `m.InReplyTo` / `m.References`
passe donc par le liant dynamique du runtime.

Cet enrichissement s'exécute sur **chaque** page de **chaque** listage de dossier
(`src/Application/Services/Implementation/OnlineMailDataProvider.cs:83-89`).
Sur une boîte de 50 000 messages : ~50 000 chaînes d'identifiants plus ~50 000
lignes à trois champs matérialisées par page, puis 50 racines × 50 000 lignes =
**2,5 millions** de recherches de sous-chaîne à répartition dynamique — par page,
par praticien, à chaque rafraîchissement.

**2. Historique patient sans pagination, avec une requête par document**
`src/Infrastructure/Repository/PatientRepository.cs:201-256` : aucun `Take`, aucune
pagination — l'intégralité de l'historique documentaire du patient est retournée.
Puis `EnrichBiologyAndAttachmentsAsync` (`:338-358`) regroupe correctement la
biologie mais émet **une requête de pièces jointes par document**, dans un
`foreach`. À noter aussi `GetMailsByInsAsync` (`:361-365`) qui délègue avec
`pageSize = int.MaxValue`.

Un patient chronique suivi plusieurs années cumule des centaines de CDA : ouvrir son
dossier matérialise tous les documents avec leur corps complet, puis enchaîne
autant d'allers-retours qu'il y a de documents. Sur une connexion lente, le délai
client peut expirer — le dossier ne s'ouvre jamais.

### Contenu attendu

1. **Comptage de fils borné sur le chemin IMAP** — porter sur
   `GetThreadCountsAsync` (`:4039`) la forme déjà livrée par task-247 :

   | Requête | Prédicat | Pourquoi cette forme |
   |---|---|---|
   | racines existantes | `MessageId IN (racines de la page)` | donne le `+1` quand la racine existe |
   | réponses directes | `InReplyTo IN (racines)` | `InReplyTo` **égale** la racine → traduisible en `IN` |
   | citations | `References LIKE '%r1%' OR … OR '%rN%'` | une citation est une **sous-chaîne**, pas une égalité → pas d'`IN`. Autant de `LIKE` que la page a de racines (25 chez le client réel), jamais la taille de la boîte |

   Réutiliser `ReferencesAnyOf` / `LoadMailsReferencingAnyRootAsync` plutôt que
   réécrire : c'est du code déjà éprouvé sur l'autre chemin.

   > ⚠️ **« Filtrer par dossier quand la sémantique le permet » — instruction
   > RETIRÉE.** C'était la rédaction d'origine, et task-247 a dû la **désobéir**,
   > mesure à l'appui. Son commentaire de code le dit : « PAS DE FILTRE PAR
   > DOSSIER, et ce n'est pas un oubli — le DOD le suggérait, la mesure de
   > comportement l'interdit. Un fil TRAVERSE les dossiers : la racine d'une
   > conversation vit couramment dans `Sent` pendant que les réponses arrivent en
   > `INBOX`. Borner au dossier de la page ferait retomber ce fil à un
   > mono-message — une régression fonctionnelle silencieuse. » Verrouillé par
   > `GetMailsByUidsAsyncCountsAThreadWhoseRootLivesInAnotherFolder`.

2. ~~**Sortir de `dynamic`**~~ — **déjà fait** par task-247 sur le chemin base
   (type nommé `ThreadLink`). À vérifier seulement : que le portage sur le chemin
   IMAP n'en réintroduise pas.
3. **Historique patient paginé** : pagination effective sur les documents et les
   mails du patient, et chargement des pièces jointes **par lot** (une requête pour
   l'ensemble de la page, pas une par document). Traiter aussi
   `pageSize = int.MaxValue`.
4. **Mesurer avant / après** : le banc de charge des tasks 173/174 existe
   précisément pour cela. Chiffrer le gain sur une boîte représentative plutôt que
   d'affirmer une amélioration.

   > ⚠️ **Constaté le 2026-08-20 — le banc n'exerce pas ce que cette task
   > optimise.** Le corpus semé ne porte **ni `In-Reply-To` ni `References`**
   > (`tests/mss.mail.loadtest.seed/Program.cs:312-334`). Sur
   > `GetThreadCountsAsync`, la première requête (scan des `MessageId`) est bien
   > exercée, mais la seconde ramène **0 ligne** et la boucle
   > `racines × lignes` — les « 2,5 millions de recherches de sous-chaîne »
   > chiffrées plus haut, c'est-à-dire **le coût dominant** — tourne **à vide**.
   > Une campagne sur le corpus actuel conclurait donc à un gain modeste par
   > défaut d'exercice, pas par faiblesse du correctif.
   >
   > **task-267** sème des fils dans le corpus. Deux options, à trancher au
   > moment de la livraison : attendre task-267 pour produire une mesure
   > opposable, ou mesurer sans elle **en énonçant explicitement** que le
   > comptage n'est pas exercé. Ce qui n'est pas acceptable, c'est de publier un
   > chiffre sans dire lequel des deux cas s'applique.
5. **Ne pas régresser fonctionnellement** : les compteurs de fils et le contenu du
   dossier patient doivent rester **identiques** — seul le coût change. C'est la
   condition pour que ce soit une task de performance et non un changement de
   comportement.

### La sémantique à préserver — c'est ici que se joue la non-régression

Le périmètre du comptage n'est **jamais** la page : seules les **racines**
viennent de la page (au plus une par message affiché) ; les **descendants** sont
cherchés dans **toute la base**. Un fil dont les membres sont dix pages plus loin
est compté aujourd'hui et doit continuer de l'être. « Borner à la page » veut
dire *ne plus matérialiser la table pour répondre sur 25 racines*, pas *ne
regarder que la page*.

Cinq propriétés du comptage actuel doivent survivre **à l'identique**. Chacune a
été trouvée sur pièce, et une réécriture « plus propre » en casserait au moins
une :

1. **Comptage de LIGNES, pas de messages distincts.** Un même `MessageId` existe
   légitimement dans plusieurs dossiers (reçu puis mis à la corbeille — jusqu'à
   **3 lignes** relevées sur une vraie boîte). task-247 a mesuré qu'une
   déduplication par `MessageId` **faisait baisser** les compteurs, 3 → 2. La
   déduplication porte sur **`(FolderPath, Uid)`**. Un `COUNT(DISTINCT MessageId)`
   en SQL reproduirait exactement le défaut corrigé.
2. **Un mail qui satisfait les deux critères compte UNE fois.** Répondre à la
   racine **et** la citer dans `References` est le cas courant. Deux agrégations
   additionnées double-compteraient.
3. **Correspondance par sous-chaîne sur `References`, sensible à la casse.**
   `Contains` → `LIKE '%id%'`. Un passage à une comparaison par jeton (plus
   correcte en RFC 5322, les `Message-Id` étant stockés sans chevrons) **changerait
   les compteurs**. Si ce point mérite d'être corrigé, c'est une autre US.
4. **Le `+1` de la racine est conditionnel** à son existence en base, et le
   résultat n'est retenu qu'à partir de **2** — un mono-message reste absent de la
   table de compteurs (`GetThreadCount` rend alors `isThreadRoot ? 1 : 0`).
5. **L'exclusion du dossier `Sent`, propre au chemin IMAP, est conservée.**
   C'est le point délicat : les deux chemins **divergent aujourd'hui**.

   | | `:4039` (IMAP — à corriger) | `~:1600` (base — corrigé par 247) |
   |---|---|---|
   | dossier `Sent` | **exclu** des deux requêtes | **inclus**, délibérément |

   Conséquence concrète : une conversation que le praticien a **initiée** (racine
   dans `Sent`, une réponse en `INBOX`) affiche « 2 messages » sur un chemin et
   **rien** sur l'autre — sans la racine le total tombe à 1, sous le seuil.

   **Décision pour cette task** : le portage **reproduit l'exclusion `Sent`** du
   chemin IMAP. Les compteurs restent strictement inchangés, le point 5 de
   « Contenu attendu » est tenu, et task-194 reste une pure US de performance.
   Le geste naturel — réutiliser tel quel le code de task-247, qui n'exclut pas
   `Sent` — **changerait les compteurs** et transformerait cette task en
   changement de comportement non validé.

   **Laquelle des deux sémantiques est la bonne est une question produit
   ouverte** → **task-268**. Elle n'est pas tranchée ici.

### Hors scope

- L'identité des mails → task-179 (mais s'aligner dessus si elle est livrée avant).
- **Unifier la sémantique de comptage entre les deux chemins** (exclusion de
  `Sent`) → **task-268**. C'est un changement de comportement, il ne se glisse pas
  dans une task de performance.
- **Corriger la correspondance par sous-chaîne sur `References`** en comparaison
  par jeton : plus correct au sens RFC 5322, mais cela changerait les compteurs.
  US séparée si le besoin est confirmé.
- La pertinence de la recherche → task-192.
- Toute modification du contrat d'API (la pagination doit s'appuyer sur les
  paramètres existants ; si un nouveau paramètre s'avère nécessaire, le documenter et
  prévoir un défaut compatible).

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test : le comptage de fils ne charge plus l'intégralité de la table — vérifié
      par assertion sur le SQL émis ou sur le nombre de lignes matérialisées (ce test
      doit échouer sur le code actuel — le vérifier explicitement)
- [ ] Test de non-régression fonctionnelle : les compteurs de fils retournés sont
      **identiques** à ceux du code actuel sur un jeu de données de référence
      (messages avec `In-Reply-To` et `References` variés)
- [ ] Test : un fil dont un membre est **sur une autre page** que la racine est
      compté — le périmètre du comptage reste la base, pas la page
- [ ] Test : un fil dont la racine vit **dans un autre dossier** est compté (hors
      `Sent` sur le chemin IMAP, cf. « La sémantique à préserver »)
- [ ] Test : le **même `MessageId` présent dans plusieurs dossiers** compte pour
      autant de lignes — les fixtures doivent porter des doublons de `MessageId`,
      sans quoi le test ne peut structurellement pas voir le défaut que task-247 a
      mesuré (3 → 2)
- [ ] Test : un mail qui **répond à la racine ET la cite** dans `References`
      compte une seule fois
- [ ] Test : l'exclusion du dossier `Sent` sur le chemin IMAP est **préservée** —
      test de verrouillage explicite, il n'en existe aucun aujourd'hui
- [ ] Test : l'historique documentaire du patient est paginé, et les pièces jointes
      sont chargées par lot (nombre de requêtes indépendant du nombre de documents)
- [ ] Test de non-régression fonctionnelle : le contenu du dossier patient (mêmes
      documents, même ordre) est inchangé
- [ ] Plus aucun `dynamic` sur le chemin de comptage de fils (déjà vrai sur le
      chemin base depuis task-247 — vérifier que le portage n'en réintroduit pas)
- [ ] **Mesures chiffrées avant / après** consignées dans la task, obtenues sur le
      banc de charge (tasks 173/174) avec une boîte représentative : latence p50/p95
      du listage de dossier, et temps d'ouverture d'un dossier patient fourni
- [ ] Le rapport de mesure précise si le corpus portait des fils (cf. task-267).
      À défaut, il **énonce** que le comptage n'a pas été exercé et que le gain
      publié ne couvre que le scan
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

1. Préparer le banc : profil de charge des tasks 173/174 avec une boîte fournie
   (idéalement ≥ 10 000 messages ; à défaut, documenter le volume atteint) et un
   patient de test porteur de nombreux documents.
2. **Mesure avant** : lancer le backend, mesurer la latence d'un listage de dossier
   (scénario `read` du banc, p50/p95) et chronométrer l'ouverture du dossier patient
   fourni. Consigner les chiffres.
3. Appliquer le correctif, relancer les **mêmes** mesures. **Attendu** : baisse
   nette et chiffrée, et une latence qui ne croît plus avec la taille totale de la
   boîte.
4. **Non-régression fonctionnelle** : comparer côte à côte, avant et après, les
   compteurs de fils affichés sur plusieurs pages d'un dossier à discussions —
   valeurs identiques.
5. Ouvrir le dossier du patient fourni : mêmes documents, même ordre, mêmes pièces
   jointes qu'avant, mais ouverture rapide et sans expiration de délai.
6. Observer la mémoire du serveur pendant un parcours de plusieurs pages : elle ne
   doit plus suivre le volume total de la boîte.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors exigence DSR spécifique — sujet de performance ; contribue
  indirectement à l'utilisabilité du LPS sur le volet MSSanté
- **Exigences DSR honorées** : non applicable — aucune exigence fonctionnelle
  nouvelle
- **INS** : non applicable — aucune règle d'identité modifiée
- **Authentification PS** : inchangée
- **Habilitations** : inchangées — le périmètre des données lues doit rester
  strictement identique (attention à ne pas élargir un filtre en optimisant)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé — ne pas réduire la journalisation existante en
  optimisant les requêtes
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement, aucun changement de
  périmètre de données.
