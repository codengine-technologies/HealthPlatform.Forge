# todo-task-485.md — Surlignage : les mots cherchés, pas les mots ignorés

**Repos**: client-angular, api-mail
**Dependencies**: —
**Epic**: E023
**Single frontend**: true

> Retour humain du 2026-11-15, sur la recherche « Clinique du Belvédère » : dans le détail d'un compte rendu,
> « du » est surligné partout, y compris au milieu des mots (« pro**du**its », « **du**rant »). Le seul vrai
> résultat, « Clinique du Belvédère », est noyé dans le bruit.

## Objectif

Dans le détail d'un message ouvert depuis une recherche, le médecin voit surlignés **les mots que la recherche a
réellement cherchés**, et la phrase entière quand il l'a trouvée telle quelle. Rien d'autre.

### Constat

- Le détail (weda2) ne surligne pas les mots du serveur : il découpe lui-même le texte tapé
  (`searchTermsOf`, `libs/mss/src/core/utils/text-highlight.util.ts`, appelé par `mail-detail.component.ts`).
- Ses règles divergent de celles de la recherche (`SearchTerms.Parse`, api-mail) :

  | | Recherche (api-mail) | Surlignage du détail (weda2) |
  |---|---|---|
  | Longueur minimale | 3 caractères | 2 caractères |
  | Mots vides (« du », « de », « la »…) | écartés | gardés |
  | « Clinique du Belvédère » | `clinique`, `belvedere` | `clinique`, `du`, `belvedere` |

- Les **extraits** de la liste de résultats n'ont pas ce défaut : ils surlignent les positions rendues par le
  serveur (`SearchHitDto.Highlights`). Ils ne changent pas.

### Règles

1. **Mêmes mots que la recherche** : un mot tapé n'est surligné que s'il a 3 caractères ou plus et n'est pas un mot
   vide. La liste des mots vides est **recopiée** depuis `SearchQueryHelper.StopWords`
   (`Api/Mail/src/Application/Helpers/SearchQueryHelper.cs`), fichier source cité en commentaire (consigne
   `code-externe-recopie`). Comparaison sans accent ni casse, comme aujourd'hui.
2. **La phrase entière quand elle y est** : un mot ignoré qui se trouve **entre deux mots cherchés** est surligné
   avec eux, d'un seul bloc (« **Clinique du Belvédère** »), au plus **3 mots ignorés** entre deux mots cherchés.
   C'est la même règle que le classement « côte à côte » d'api-mail (PR #370, `SearchTextSchema.AdjacentPattern`) :
   ce qui est surligné en bloc et ce qui est classé en tête coïncident. Un vrai mot entre les deux casse le bloc
   (« clinique Saint-Jean, transmis au Belvédère » : deux surlignages séparés).
3. **Un mot cherché trouvé dans un autre mot reste surligné** (« kaliémie » dans « hypokaliémie ») : la recherche
   le trouve aussi, le surlignage doit le montrer. Un mot ignoré ne l'est jamais seul, ni dans un autre mot.
4. **Partout dans le détail** où le surlignage existe : sujet, corps texte, corps HTML, document médical (cadre
   isolé `medical-html-frame`), noms des pièces jointes.
5. **Rien n'est cherché, rien n'est surligné** : une recherche faite uniquement de mots ignorés (« de la ») ne
   surligne rien.

### Hors périmètre

- **client-mobile** : son détail ne surligne pas les mots cherchés (lecture enrichie attendue avec la refonte mobile
  de la recherche). Le scénario y est `non-applicable` pour cette raison fonctionnelle.
- Le serveur ne change pas : les règles 1 et 2 existent déjà côté recherche. api-mail n'est listé que pour le
  catalogue e2e (`e2e/scenarios.yml`).

## Definition of Done

- [ ] Build passes (`nx build weda2`, 0 erreur)
- [ ] Tests pass (`nx test mss-lib`, `nx test weda2` : 0 échec)
- [ ] Tests unitaires de `searchTermsOf` et du calcul des plages, chacun **vu rouge par mutation** :
      « Clinique du Belvédère » → un seul bloc ; « du » seul ou dans « produits » / « durant » jamais surligné ;
      mot de 2 caractères écarté ; « kaliémie » surligné dans « hypokaliémie » ; vrai mot entre deux mots cherchés
      → deux blocs ; plus de 3 mots ignorés → deux blocs ; requête faite de mots ignorés → aucun surlignage ;
      accents et casse sans effet (« belvedere » surligne « Belvédère »).
- [ ] Test de composant du détail : le corps HTML et le document médical surlignent le bloc et pas les « du » isolés.
- [ ] Liste des mots vides recopiée de `SearchQueryHelper.StopWords`, source citée en commentaire.
- [ ] Scénario `E2E-SEARCH-015` v1 ajouté dans `Api/Mail/e2e/scenarios.yml` — « Le détail surligne ce qui a été
      cherché » ; attendu : après la recherche « Clinique du Belvédère », le détail du message surligne « Clinique du
      Belvédère » d'un bloc, et aucun « du » ailleurs (ni seul, ni dans un mot). Clients : `angular: requis`,
      `mobile: non-applicable` (le détail mobile ne surligne pas). Implémenté dans la suite Angular (`mss-e2e`).
- [ ] Trou du filet : `E2E-SEARCH-015` prouvé rouge sur le surlignage non corrigé, ligne ajoutée dans
      `conventions/e2e.md` (le surlignage du détail n'était couvert par aucun parcours : E2E-SEARCH-010 ne lit que
      l'extrait).
- [ ] data-testid inchangés ou ajoutés sur les éléments lus par le scénario.
- [ ] Aucune donnée de santé dans les journaux (le surlignage reste côté client, rien n'est journalisé).

## Manual Test Plan

- Lancer l'AppHost api-mail, puis weda2 : `cd Client/Angular/front && npm run start:weda2`.
- Ouvrir la messagerie sur la boîte de test (Virginie), lancer la recherche `Clinique du Belvédère`.
- Ouvrir le message UID 5255 (compte rendu d'accouchement) :
  - **attendu** : « Clinique du Belvédère » surligné d'un bloc dans « Mode de sortie » ;
  - **attendu** : aucun « du » surligné ailleurs (« Transfusion de produits », « Pathologie durant le travail »,
    « Etat du périnée »).
- Rechercher `kaliemie` sur un compte rendu de biologie qui contient « hypokaliémie » : le mot reste surligné dans
  « hypokaliémie ».
- Rechercher `de la` : la recherche ne cherche rien, et le détail ne surligne rien.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — confort de lecture de la messagerie, sans exigence DSR
- **Exigences DSR honorées** : non applicable — affichage côté client seulement
- **INS** : non applicable — aucun patient manipulé ni identifié
- **Authentification PS** : inchangée — PSC / e-CPS de la session messagerie
- **Habilitations** : inchangées — le détail n'affiche que les messages de la boîte ouverte (règle 14)
- **Interop CI-SIS** : non applicable — le document CDA est affiché tel que reçu ; seul le surlignage change
- **Tracé PGSSI-S** : aucun nouvel évènement — la lecture du message est déjà tracée, le surlignage ne l'est pas
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — aucune donnée nouvelle stockée ni transmise
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau


## Branches

- `api-mail` (pushed) : feat/task-485-surlignage-les-mots-cherches-pas-les — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-485-surlignage-les-mots-cherches-pas-les
- `client-angular` (code-only) : la forge écrit sur la branche courante de `Client/Angular/` (au /start :
  `feature/nova-mss-weda-integration`, arbre portant le code non commité de task-487) — l'humain gère branche, commit,
  push, PR TFS

## Develop log

### client-angular (weda2, code-only)

- **`core/utils/text-highlight.util.ts`** :
  - `searchTermsOf` garde les mots de 3 caractères ou plus, hors mots vides : mêmes règles que `SearchTerms.Parse`
    (api-mail). La liste `SEARCH_STOP_WORDS` est recopiée de `SearchQueryHelper.StopWords`, source citée, même
    découpage de lignes (`// prettier-ignore`) ; identité vérifiée par script (144 mots des deux côtés).
  - `findTermRanges` lie d'un bloc deux mots cherchés **différents** que séparent seulement des séparateurs et au plus
    3 mots ignorés (`bridgesTerms`, `MAX_IGNORED_WORDS_BETWEEN`), comme `SearchTextSchema.AdjacentPattern`. Un même mot
    répété (« Hémoglobine, hémoglobine ») reste deux surlignages ; un vrai mot entre deux mots cherchés coupe le bloc.
  - Le calcul est le même pour l'objet, le corps texte, le corps HTML, le document médical et les noms de pièces : tous
    passent par `searchTermsOf` puis `findTermRanges` / `highlightHtml`.
- **Tests** (Vitest, lancés **via PowerShell** : depuis Git Bash, le lanceur échoue en bloc, mémoire
  `vitest-mss-lanceur-instable-ngmodule`) :
  - `text-highlight.util.spec.ts` : 24/24, dont 9 tests de task-485 (bloc « Clinique du Belvédère », « du » seul ou
    dans un mot, mot de 2 caractères, « kaliémie » dans « hypokaliémie », vrai mot entre deux mots cherchés, un seul
    vrai mot, au plus 3 mots ignorés, recherche faite de mots ignorés, accents et casse, corps HTML). Le test
    « Catherine BERNARD » attend désormais un seul bloc (changement voulu, règle 2).
  - `mail-body.component.spec.ts` (22/22) : corps HTML et document médical surlignent le bloc, aucun « du » isolé.
  - `mail-detail.search-highlight.spec.ts` (5/5) : seuls « Clinique », « Belvédère » sont transmis au corps ; l'objet
    surligne le bloc.
  - Suite mss-lib complète : 174 fichiers, **1 889/1 889**.
- **Preuves rouges** :
  - 7 tests de l'utilitaire rouges avant le correctif ; les deux tests de composant rouges sur l'utilitaire d'avant
    (version TFS de `HEAD`), verts sur le correctif.
  - Mutations (`mutate_highlight.py`) : M1 3 → 2 mots ignorés, M2 longueur 3 → 2, M3 mots vides oubliés, M4 un même mot
    se lie, M6 aucun bloc : **tuées**. M5 (tout mot de l'écart réputé ignoré) **survivait** — le seul test « vrai mot »
    avait 4 mots dans l'écart, coupé par la limite de 3 ; test « un seul vrai mot » ajouté (« Clinique Pasteur du
    Belvédère »), M5 **tuée** ensuite.

### api-mail

- Catalogue : **E2E-SEARCH-015** v1 (angular requis ; mobile non-applicable, raison au catalogue), après
  E2E-SEARCH-012 ; `ScenarioCatalogTests` 17/17 avant le push (consigne `catalogue-edite-sans-son-test`). Commit
  `28ce310f`. Aucun code serveur modifié.

### E2E

- Scénario implémenté dans `e2e/mss-e2e/specs/functional.e2e.ts` : message déposé hors de l'application (corps texte
  « Mode de sortie : Clinique du Belvédère », « produits », « durant », « état du périnée »), recherche « Clinique du
  Belvédère », résultat ouvert ; les surlignages du corps sont exactement `['Clinique du Belvédère']`.
- **Preuve rouge (trou du filet)** sur le banc `--serve-only`, weda2 servi avec l'utilitaire d'avant (version TFS de
  `HEAD`) : rouge sur l'assertion du surlignage, 7 marques (`du`, `Clinique`, `du`, `Belvédère`, `du`, `du`, `du`).
  Correctif restauré, recompilation : **vert deux fois**. Démontage complet (ports libres, aucun conteneur).
- Défaut de mon test trouvé en route : la prémisse lisait `isVisible()` aussitôt après la réponse de recherche (rouge
  sans rapport avec le code, message pourtant à l'écran) ; attente du rendu ajoutée, convention
  `attendre-le-rendu-apres-la-reponse` créée dans `conventions/e2e.md`. Ligne « Trous du filet » ajoutée.
- weda2 : `nx test weda2` 107 fichiers verts, `nx build weda2` OK (dépassements de budget déjà présents : 2,40 Mo,
  `mss-contacts.component.scss`) ; ESLint et prettier propres. Vert client-angular marqué.

## Code Review Summary

### Passage 1 (revue anticipée) — APPROVED

Relecteur indépendant (sous-agent, code et US seulement). **approved at** : api-mail `28ce310f` (catalogue seul) ;
client-angular : arbre de travail de `feature/nova-mss-weda-integration` (HEAD `c434dd3e`) au 2026-11-19 (code-only).

- **Règle 1b** : aucun comportement atteignable par une route ne change (api-mail : catalogue e2e seulement).
- **api-mcp** : aucun impact (`mcp_impact.py check` → 0).
- **DoD, scénario** : E2E-SEARCH-015 v1 au catalogue, même version dans la spec weda2 (`scenario('E2E-SEARCH-015', 1)`).
- **Revue** : règles 1, 2, 3, 5 respectées ; liste des mots vides identique à `SearchQueryHelper.StopWords` ; constantes
  alignées sur le serveur (3 caractères, 3 mots ignorés) ; les extraits des résultats ne changent pas
  (`mail-search-results.component.ts` n'utilise que `highlightSegments` sur les positions du serveur) ; aucun HTML reçu
  injecté. Cas vérifiés : un bloc ne relie que deux mots cherchés, un mot ignoré n'entre jamais en morceau, « Clinique
  du Clinique » → deux blocs, trois mots cherchés à la suite → un bloc, ordre inverse lié.

#### Suggestions (non bloquantes)

- **Ligatures** (antérieur, task-446) : `foldChar` ne décompose pas « œ », « æ », que le serveur écrit « oe », « ae » :
  « oedeme » trouve « œdème » mais ne le surligne pas (« œdème », « cœur », « œsophage » sont courants). Recopier la
  table `Ligatures` de `SearchTerms` ; test « oedeme » → « Œdème ». **Recommandé en task séparée.**
- Plafond `MaxSearchTerms` (10 mots) non appliqué au surlignage : un 11ᵉ mot serait surligné sans avoir été cherché.
- Saisie en forme décomposée (NFD) découpée avant repliement : `query.normalize('NFC')` avant le découpage.
- Garde de l'écart (`^[^\p{L}\p{N}]` / `[^\p{L}\p{N}]$`) jamais testée : cas « ere » au milieu de « Belvédère »
  juste après un pont.
- Pas de bloc à travers deux nœuds HTML (« Clinique <b>du</b> Belvédère » → deux surlignages, « du » non surligné) :
  limite à documenter.
- Règle 4, noms des pièces jointes : aucun surlignage n'existe aujourd'hui sur ces noms dans le détail ; rien à changer
  (« là où le surlignage existe »), à savoir pour la recette.
- E2E-SEARCH-015 : la prémisse lit une ligne générique (`MAIL_ROW`) ; l'assertion principale (exactement
  `['Clinique du Belvédère']`) ne peut pas mentir. Durcissement possible : chercher la ligne dans les résultats.

## Sonar log

- **Sonar : non joué (skip mesuré)** — la seule modification d'api-mail est le catalogue e2e (`e2e/scenarios.yml`,
  commit `28ce310f`), hors du périmètre analysé par Sonar (code C#). Une analyse ne mesurerait rien de nouveau sur ce
  code. Aucune dette introduite côté serveur.
- Écart au playbook, signalé : `agents/sonar.md` ne prévoit le skip que pour « aucun commit api-mail ». Suggestion :
  étendre ce skip au cas « aucun fichier du périmètre Sonar modifié » (changement du plan de contrôle, relu par
  l'humain avant push).

## Lint log

- Mode A (chaîné), scope `tag:scope:mss`, base `origin/next` ; aucun override.
- Comptage : `npx eslint libs/mss apps/mss e2e/mss-e2e --format json` (contournement de task-367) ; attribution par
  `git diff -U0 HEAD` + fichiers non suivis.
- Résultat : **0 erreur**, 100 avertissements (75 `jsdoc/require-example`, 22 `max-lines`, 3 `complexity`), **aucun sur
  une ligne de la task**. Itérations : 0 / 5, aucun fichier modifié. Prettier propre sur les fichiers de la task.
- Build / tests non rejoués : vert de `/develop` valide sur cet arbre (`green.py check` : `c434dd3e`).
- L'arbre porte aussi, non commités, les correctifs d'après merge de task-487 (`chat-bubble.*`,
  `mail-conversation.component.{scss,spec.ts}`) : à commiter sur TFS par l'humain, avec ou sans task-485.

## Timings

*(généré par `tools/timing/report.sh --task task-485 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 17 s | — | — | — | — |
| /develop | ok | 1 h 12 min | — | — | — | — |
| /review-code | ok | 3 min 14 s | — | — | — | — |
| /sonar | skipped | 0.8 s | — | — | — | api-mail : catalogue e2e (YAML) seul, aucun fichier analysé par Sonar |
| /lint-angular | ok | 28 s | — | — | — | — |
| **Total cycle** | | **1 h 16 min** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×1 (9.7 s)
