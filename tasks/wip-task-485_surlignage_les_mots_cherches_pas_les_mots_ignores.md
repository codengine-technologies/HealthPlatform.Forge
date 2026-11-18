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

## Timings

*(généré par `tools/timing/report.sh --task task-485 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 17 s | — | — | — | — |
| **Total cycle** | | **17 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
