# todo-task-439.md — Recherche plein texte fiable : accents, champs, tous les mots, tout l'historique

**Repos**: api-mail, dtos-mss
**Dependencies**: done-task-438
**Epic**: E022
**Single frontend**: true
**Priorité**: EPIC E022, demandée par l'humain le 2026-11-09. Absorbe task-436 (coût du plein texte), sur décision de
l'humain du même jour : « une seule refonte, une seule migration éventuelle ».

> **Origine.**
> - Campagne du 2026-11-09 : `Docs/audits/recherche-campagne-bugs-weda2-mobile-20261109.md`, défauts **R1 à R5**.
> - Coût : `Docs/audits/api-mail-volumetrie-plans-boite-11k-20261109.md` (ex-task-436), plans et `replay.py` dans
>   `Docs/audits/findings/plans/20261109-volumetrie-boite-11k/`.
> - Requêtes de référence et corpus : task-438. Les cas marqués « task-439 » y passent au vert ici.

## Ce qui est établi

**Ce que rate le médecin** (boîte de 11 178 mails, appels réels, 2026-11-09) :

| Défaut | Requête | Vérité terrain | Rendu |
|---|---|---|---|
| R1 accent oublié | `hemoglobine` | 804 messages contiennent « hémoglobine » | 2 (seuil 0,7) |
| R2 objet non cherché | `urgent` | 72 messages, dont 67 par l'objet seul | 5 |
| R3 historique ancien | `Catherine BERNARD` | 51 messages portent les deux noms | 22 ; **tous les manquants sont les plus anciens** |
| R4 un des mots (OU) | `Catherine BERNARD` | — | 28 résultats sur 50 n'ont qu'un des deux noms |
| R4 termes abandonnés | `bilan lipidique cholestérol total` | 35 messages ont les quatre mots | 27 ; « total » jamais cherché |
| R5 ponctuation | `cholestérol,` | 47 messages contiennent « cholestérol » | 0 |

**Causes** (`405da376`) :
- `SearchQueryHelper.FilterSearchTerms` : découpe sur les espaces seulement (la ponctuation reste collée), ignore les
  mots de 2 lettres ou moins, garde les **3 termes les plus longs** (`SemanticSearchRepository`, ligne 734).
- `MailContentsSinglePassSql` / `MedicalDocumentsSinglePassSql` (lignes 711 et 715) : `lower(Body) LIKE '%terme%'`,
  **sans repli des accents**, sur le **corps seul** des messages et des documents. Les termes sont combinés en **OU**.
- `SearchLimits.FullTextCandidatesPerTerm = 200` : chaque terme ne garde que ses 200 correspondances **les plus
  récentes** avant tout classement. Un nom fréquent épuise ce quota avec d'autres patients. Le test
  `Semantic_MoreMatchesThanTheWindow_KeepsTheMostRecentMails` fige ce comportement (marqué task-439 par task-438).

**Coût** (repris de task-436) : la recherche plein texte des contenus passe de 11,65 ms (156 mails) à **134,73 ms**
(11 178 mails), celle des documents de 8,69 à 31,70 ms. Cause : l'application renvoie à Postgres, en `ANY($2)`, les
identifiants de **tous** les contenus du dossier, puis met chaque corps en minuscules. L'index `pg_trgm` avait été
écarté par task-427 sur une boîte de 156 mails : verdict à remesurer à 11 000 mails.

**Déploiement** : une base est migrée à son premier accès, sous un sémaphore commun à toutes les boîtes du processus
(`BaseRepository.HandleEnvironmentDbSetupAsync`). Un index construit dans une migration ordinaire bloquerait l'ouverture
de toutes les boîtes (même contrainte que task-437).

## Objective

Le médecin trouve **tous** les messages de sa boîte qui contiennent ce qu'il a tapé, quelle que soit sa façon de le
taper, dans les champs où il s'attend à le trouver, sur tout l'historique de la boîte. Ceux qui contiennent tous ses mots
viennent d'abord.

Règles métier (décisions de l'humain du 2026-11-09) :
- **Accents, casse et ponctuation sans effet** : `hemoglobine`, `HÉMOGLOBINE`, `hémoglobine,` trouvent les mêmes
  messages. La requête est découpée en mots sur tout ce qui n'est ni lettre ni chiffre.
- **Champs cherchés** : objet, corps du message, corps des documents médicaux (CDA, HPRIM), nom et adresse de
  l'expéditeur, nom des pièces jointes.
- **Tous les mots d'abord** :
  - premier groupe : les messages qui contiennent **tous** les mots significatifs ;
  - second groupe, **séparé et signalé** : ceux qui n'en contiennent qu'une partie, du plus grand nombre de mots au plus
    petit ;
  - dans chaque groupe, du plus récent au plus ancien ;
  - chaque résultat dit à quel groupe il appartient (contrat, ci-dessous).
- **Tous les mots significatifs comptent**, jusqu'à 10 ; au-delà, la réponse le signale. Les mots vides restent ignorés.
- **Tout l'historique** : aucune correspondance n'est écartée parce qu'elle est ancienne. Le plafond de candidats par
  terme choisis parmi les plus récents disparaît.
- **Voir les suivants** : quand il y a plus de résultats que la page demandée, la réponse le dit (`isTruncated`) et le
  client peut demander la page suivante.
- **Règle 14 inchangée** : même base de la boîte, même verdict de l'opérateur, même trace de la recherche au nom de la
  personne réelle.

Contrat (`dtos-mss`, rétrocompatible) :
- chaque `hit` porte son **groupe de correspondance** (tous les mots / une partie des mots) ;
- la requête accepte une **position de départ** (page suivante) ;
- les champs existants (`uids`, `hits`, `isTruncated`, `isDegraded`) gardent leur sens. Les clients actuels, qui ne
  lisent que `uids`, continuent de fonctionner ; l'affichage des groupes et des pages suivantes est task-441.

Exigences de coût (reprises de task-436), mesurées sur la boîte de 11 178 mails :
- la partie plein texte d'une recherche ne renvoie plus à Postgres la liste des identifiants du dossier ;
- elle coûte **45 ms au plus** sur les contenus et **15 ms au plus** sur les documents, plans à l'appui, alors qu'elle
  cherche désormais dans plus de champs ;
- au moins deux pistes sont mesurées et consignées avant le choix (index sur un texte normalisé, `pg_trgm`, recherche
  plein texte Postgres, colonne de texte cherchable…) : taille, temps de construction, temps de requête ;
- **un index ne bloque pas les autres boîtes** : sa construction ne retarde l'ouverture d'aucune autre boîte, et une
  boîte dont l'index n'existe pas encore cherche quand même (mécanisme partagé avec task-437 si les deux en posent un).

### Hors périmètre

- Les résultats sémantiques et leur place dans la réponse : task-440. L'index vectoriel : task-437.
- L'affichage côté clients (groupes, pages suivantes, ordre) : task-441.
- La recherche avancée par filtres (inchangée), et `/search/patient` (inchangée, hors corpus des défauts constatés).

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`, `HealthPlatform.Dtos.Mss.csproj`
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`
- [ ] **Les requêtes de référence de task-438 marquées « task-439 » sont vertes**, marquage retiré : accent oublié,
      majuscules, ponctuation, mot de l'objet, de l'expéditeur, du nom d'une pièce jointe, patient au long historique
      (rappel 100 % sur ses messages), plusieurs mots (tous les mots en tête, partiels signalés), plus de 3 mots
- [ ] **Test d'intégration de bout en bout (règle 1b), `POST /api/v1/Search/semantic`** en mode hybride, lu dans la
      réponse réelle :
      - un patient dont plus de 200 messages portent le nom : **tous** sont trouvés, les plus anciens compris, page par
        page ;
      - le groupe de correspondance de chaque `hit` est lu et vaut ce qu'il doit valoir ;
      - **vu rouge** sur le code d'avant (cas de task-438) et par mutation (plafond par terme réinjecté, puis restauré et
        recompilé), preuve consignée dans le `## Develop log`
- [ ] **Cas d'échec** : une requête sans mot significatif rend la même réponse qu'aujourd'hui (liste vide, sans
      erreur) ; une requête de plus de 10 mots le signale dans la réponse
- [ ] Le test `Semantic_MoreMatchesThanTheWindow_KeepsTheMostRecentMails` est **réécrit** selon la nouvelle règle (tout
      l'historique, page par page), pas supprimé
- [ ] Contrat `dtos-mss` publié (NuGet) et consommateurs .NET mis à jour ; rétrocompatibilité vérifiée : un client qui
      ne lit que `uids` reçoit la même forme de réponse
- [ ] **Coût** mesuré sur la boîte de 11 178 mails par `replay.py` (formes nouvelles) : plein texte des contenus
      ≤ 45 ms, des documents ≤ 15 ms ; tableau des pistes mesurées dans le `## Develop log`
- [ ] Si un index est posé : migration auditée (règle 7c), construction sans blocage des autres boîtes prouvée par un
      test d'intégration (une boîte A s'ouvre pendant la construction de l'index d'une boîte B), base neuve et base
      existante testées
- [ ] **A/B au banc** (tir court 1400 → 1996, IA simulée, contre `bilan-apres` dans la même session) : temps SQL des
      formes de recherche, p50 / p95 de l'étape « recherche »
- [ ] Outil de campagne de task-438 rejoué sur la boîte de formation de Virginie : R1 à R5 disparus, tableau consigné
- [ ] Aucune donnée de santé en clair dans les logs (termes de recherche compris)
- [ ] **Prévention (règle d'or)** : consigne dans `conventions/csharp.md` : un plafond de candidats ne se choisit jamais
      par ancienneté avant le classement ; une liste d'identifiants qui croît avec la boîte ne se renvoie jamais en
      paramètre

## Manual Test Plan

1. Lancer le backend sur la boîte de formation de Virginie : `cd Api/Mail/src/AppHost && dotnet run`.
2. Dans weda2 (connexion par la CPS de Virginie), boîte de réception, rechercher successivement :
   `hemoglobine`, `HÉMOGLOBINE`, `cholestérol,`, `urgent`, `Catherine BERNARD`, `bilan lipidique cholestérol total`.
3. Attendu :
   - `hemoglobine` et `HÉMOGLOBINE` rendent les mêmes messages, qui contiennent « hémoglobine » ;
   - `cholestérol,` trouve les messages qui contiennent « cholestérol » ;
   - `urgent` trouve les messages dont l'objet contient « URGENT » ;
   - `Catherine BERNARD` : les messages de Catherine BERNARD d'abord, y compris les plus anciens (l'outil de campagne
     compte 51 messages ; l'affichage des groupes arrive avec task-441) ;
   - dans Seq, la route `POST /api/v1/Search/semantic` reste rapide.
4. Rejouer l'outil de campagne de task-438 : R1 à R5 n'apparaissent plus.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du praticien)
- **Vague Ségur** : hors Ségur — fiabilité de la recherche dans la messagerie
- **Exigences DSR honorées** : non applicable — aucune exigence DSR ne porte sur la recherche de la messagerie
- **INS** : non applicable — la recherche ne lit ni n'écrit l'INS ; un nom de patient est cherché comme un mot
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : inchangées — verdict de l'opérateur MSSanté sur la boîte (règle 14)
- **Interop CI-SIS** : non applicable — les documents CDA et HPRIM déjà analysés sont cherchés, pas échangés
- **Tracé PGSSI-S** : inchangé — chaque recherche tracée au nom de la personne réelle (`MailSearch`), 3 653 jours ;
  les termes ne sont jamais écrits dans les journaux
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — un éventuel index ou texte normalisé porte des données de santé et vit dans la base de la
  boîte, avec ses sauvegardes et sa suppression
- **AIPD / impact RGPD** : inchangé — aucune donnée nouvelle ; les structures de recherche sont dérivées de la boîte

## Branches
- `api-mail` (pushed) : feat/task-439-recherche-plein-texte-fiable-accents — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-439-recherche-plein-texte-fiable-accents
- `dtos-mss` (paresseuse) : branche `feat/task-439-recherche-plein-texte-fiable-accents` créée par `/develop` depuis `origin/develop` au moment où il touche le contrat (groupe de correspondance, position de départ)

## Timings

*(généré par `tools/timing/report.sh --task task-439 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 18 s | — | — | — | — |
| **Total cycle** | | **18 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
