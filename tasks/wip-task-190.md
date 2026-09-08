# todo-task-190.md — Tableaux de résultats illisibles à l'impression : les cellules sont collées

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axes surface HTTP et
> métier MSSanté).

> ### ⚠️ Re-vérification du 2026-09-08 — **périmètre réduit de moitié**
>
> Cette task portait **deux** défauts. Le premier — le 500 systématique sous
> Kestrel — **n'existe plus**, et n'existait déjà plus quand la re-vérification
> du 2026-08-23 l'a coché « inchangé ». Seul le second reste ouvert.
>
> | Preuve d'origine | Au 2026-09-08 | État |
> |---|---|---|
> | Écriture synchrone du PDF vers `Response.Body` | **CORRIGÉ** — `MailExportController.cs:135-137` bufferise via `FileBufferingWriteStream` puis `DrainBufferAsync`. Correctif de **task-077**, commit `930091bb` du **2026-06-11**. | **obsolète** |
> | `AllowSynchronousIO` jamais activé | confirmé — les 2 seules occurrences du repo sont des **commentaires** expliquant pourquoi on ne l'active pas | inchangé (et c'est bien) |
> | Autres endpoints de téléchargement | confirmé sains — les 4 `StreamingFileResult` du repo : ZIP et PDF via `FileBufferingWriteStream`, EML via `WriteToAsync`, vCard via `StreamWriter.WriteAsync` | **balayage déjà fait** |
> | `TD`/`TH` sans séparateur | **`MailExportService.cs:437`** — `AppendNodeText` traite `BR`, `LI`, `P/DIV/H1-H6/UL/OL/TR` et envoie **tout le reste** au `default:` sans séparateur | **inchangé** |
> | `ExtractPlainBody` préfère `BodyHtml` | **inchangé** — c'est donc le chemin normal de tout message HTML imprimé | **inchangé** |
>
> **Comment la re-vérification d'août s'est trompée.** Elle citait
> `MailExportController.cs:132-137` comme preuve du défaut. Ce sont exactement les
> lignes du **correctif** de task-077 — le `FileBufferingWriteStream` et son
> commentaire « writes synchronously into a bounded buffer, then drains
> asynchronously ». La ligne a été **relevée sans être lue**. À retenir pour les
> prochaines re-vérifications : constater qu'un numéro de ligne a bougé ne dit
> rien de ce qu'il contient.
>
> **Ce que le changement de périmètre change.** L'objectif n'est plus « la
> fonctionnalité est cassée » mais « le PDF sort, et il est illisible pour les
> tableaux ». Ce n'est plus une panne, c'est un **défaut de lisibilité clinique** —
> à traiter comme tel, sans l'urgence d'une régression de service.

## Objective

Rendre **déchiffrables** les tableaux de résultats dans le PDF produit par
l'impression et par l'export.

Les cellules HTML sont concaténées **sans séparateur**. Un hémogramme s'imprime
`Hémoglobine7,2g/dL13,0-17,0` : le libellé, la valeur, l'unité et l'intervalle de
référence sont indiscernables. C'est précisément l'artefact qui rend un résultat
imprimé inutilisable — et, plus grave, **mal interprétable** au point de soin :
rien ne dit au lecteur où finit la valeur et où commence l'intervalle.

**US backend-only (justification)** : extraction de texte et rendu côté serveur.

### Preuve (état actuel du code, vérifié le 2026-09-08)

`src/Application/Services/Implementation/MailExportService.cs`, méthode
`AppendNodeText` :

```csharp
case "P": case "DIV": case "H1": … case "UL": case "OL": case "TR":
    AppendNodeText(element, sb);
    sb.Append('\n');
    continue;
default:
    AppendNodeText(element, sb);   // ← TD et TH passent ici
    continue;
```

`TD` et `TH` tombent dans le `default:` et versent leur texte bout à bout. Seule
la fin du `TR` produit un `\n` : on obtient donc **une ligne par rangée, sans
aucune séparation entre les colonnes**.

`ExtractPlainBody` préfère `BodyHtml` dès qu'il est présent — c'est le chemin
**normal** de tout message HTML imprimé par le praticien, pas un cas limite.

### Contenu attendu

1. **Séparer les cellules.** `TD` et `TH` doivent produire un séparateur lisible.
   Le choix du séparateur est à trancher à l'implémentation et à **justifier dans
   la task** : une tabulation aligne mal en police proportionnelle (le PDF n'est
   pas du texte à chasse fixe), plusieurs espaces se collapsent visuellement, un
   séparateur visible (` | `) est lisible mais ajoute un caractère au contenu
   clinique. Contrainte qui tranche : **le lecteur doit pouvoir distinguer une
   valeur de son intervalle de référence sans ambiguïté**.
2. **Ne pas régresser le reste de l'extraction.** Paragraphes, listes (`• `),
   sauts de ligne, titres, et le collapse des lignes vides doivent rester
   identiques. Les tests existants (`BuildPdfWithHtmlBodyConvertsToPlainText`,
   `BuildPdfWithPlainTextBodyContainingHtmlTagsConverts`,
   `BuildPdfWithMedicalDocumentHtmlBodyFallback`) sont le filet.
3. **Vérifier sur un cas réel**, pas sur un tableau jouet : un hémogramme complet
   (au moins 8 lignes, colonnes libellé / valeur / unité / intervalle) et un
   tableau avec `TH` d'en-tête. Le corpus `tests/…/Resources/cda-samples` peut
   fournir un cas si un CDA en contient un.
4. **Couvrir aussi le chemin CDA.** Le repli d'extraction sert également au
   contenu de documents **CDA r2** : la lisibilité des tableaux vaut donc pour les
   comptes-rendus structurés, pas seulement pour le corps du mail.

### Ce qui a été retiré du périmètre, et pourquoi

- **Streaming asynchrone du PDF** — déjà livré par **task-077** (`930091bb`,
  2026-06-11). Rien à faire.
- **Balayage des autres endpoints de téléchargement** — déjà vérifié : les quatre
  `StreamingFileResult` du repo sont sains. Le résultat est consigné dans le
  tableau de re-vérification ci-dessus ; **ne pas le refaire**.
- **`AllowSynchronousIO`** — jamais activé, et deux commentaires du repo
  expliquent déjà pourquoi il ne doit pas l'être.

### Ce qui est conservé du périmètre d'origine

**Les tests d'intégration HTTP sur `/print` et `/export/pdf`**, bien que le défaut
qu'ils devaient démontrer soit corrigé. Deux raisons :

- **Ils n'existent pas** — vérifié : aucun test du repo n'exerce ces deux routes
  de bout en bout.
- **L'enseignement de la task d'origine reste vrai** : les tests PDF actuels
  tournent sur `MemoryStream`, qui **accepte** les écritures synchrones. Ils
  n'auraient pas vu le défaut de 2026-07, et ils ne verraient pas sa réapparition.
  Un test contre un flux qui **refuse** les écritures synchrones est un garde-fou
  de non-régression sur un piège que ce repo a déjà rencontré **deux fois** (ZIP
  puis PDF).

### Hors scope

- La refonte de la mise en page du PDF (typographie, en-têtes, colonnes alignées)
  au-delà de la lisibilité des cellules.
- La journalisation des exports, déjà en place et vérifiée.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test unitaire : un corps HTML contenant un tableau produit un texte où les
      cellules sont **séparées** — cas hémogramme, libellé / valeur / unité /
      intervalle discernables (ce test doit échouer sur le code actuel — le
      vérifier explicitement)
- [ ] Test unitaire : un tableau avec en-têtes `TH` sépare aussi ses en-têtes
- [ ] Test unitaire de non-régression : paragraphes, listes à puces, `BR`, titres
      et collapse des lignes vides **inchangés**
- [ ] Le séparateur retenu est **justifié dans la task** (§ Contenu attendu, point 1)
- [ ] Test d'intégration : `GET …/print` retourne `200` `application/pdf`
- [ ] Test d'intégration : `GET …/export/pdf` retourne `200` `application/pdf`
- [ ] Ces deux tests s'exécutent contre un flux **refusant les écritures
      synchrones** (pas un `MemoryStream` permissif) — garde-fou de non-régression
      sur le piège corrigé par task-077
- [ ] Les traces d'audit `MailPrint` / `MailExportPdf` sont **toujours** produites
      (non-régression — ne pas casser ce que task-186 a consolidé)
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. Ouvrir un message contenant un **tableau de résultats de biologie** en HTML
   (données de test anonymisées) — idéalement un hémogramme complet.
3. **Impression** : déclencher l'impression. **Attendu** : un PDF s'ouvre — c'est
   déjà le cas aujourd'hui, c'est une vérification de non-régression.
4. **Lisibilité** — le cœur du test : dans le PDF produit, chaque ligne du tableau
   doit rester déchiffrable. `Hémoglobine`, `7,2`, `g/dL`, `13,0-17,0` **séparés**.
   Avant correctif : `Hémoglobine7,2g/dL13,0-17,0`.
5. **En-têtes** : vérifier qu'une ligne d'en-tête (`TH`) est elle aussi lisible.
6. **Cas CDA** : imprimer un message porteur d'un compte-rendu structuré contenant
   un tableau → même vérification.
7. **Non-régression de mise en forme** : un message avec paragraphes et liste à
   puces s'imprime comme avant (puces `• `, sauts de ligne, pas de ligne vide en
   trop).
8. **Non-régression des voisins** : exporter le même message en EML et une fiche
   contact en vCard → toujours fonctionnels.
9. **Journal d'audit** : vérifier qu'une trace `MailPrint` et une trace
   `MailExportPdf` sont bien écrites (écran « Journal d'audit »).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — volet MSSanté
- **Exigences DSR honorées** : correctif de conformité — restitution **fidèle et
  exploitable** des documents de santé reçus (impression au point de soin)
- **INS** : non applicable — l'INS peut figurer dans le document imprimé, ce qui
  est normal et attendu dans un document destiné au dossier patient (à ne pas
  confondre avec son interdiction dans les **logs**, cf. task-184 et l'arbitrage
  de task-186)
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : le repli d'extraction concerne aussi le contenu de documents
  **CDA r2** — la lisibilité des tableaux vaut donc aussi pour les comptes-rendus
  structurés
- **Tracé PGSSI-S** : impression et export PDF sont **déjà** journalisés
  (`MailExportController.TraceMailAction`) — vérifier que la trace est toujours
  produite après correctif
- **Consentement patient** : non applicable
- **Référentiels métier** : les intervalles de référence et unités des résultats de
  biologie doivent rester lisibles — **enjeu de sécurité d'interprétation
  clinique**, c'est la justification première de cette task
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé — pas de nouveau traitement.

  > **Correction d'une alerte devenue caduque.** La version précédente de cette
  > task demandait de signaler à l'humain que la fonctionnalité était
  > **inopérante** et que les praticiens n'avaient pas pu imprimer. C'était vrai
  > entre la mise en place du chemin PDF (task-017) et son correctif
  > (**task-077, 2026-06-11**) — **pas depuis**. Ne pas transmettre cette alerte
  > telle quelle.

  L'impression fonctionne ; ce qui reste en jeu est la **qualité de restitution**
  d'un document imprimé et versé au dossier patient.

## Develop log

### Séparateur retenu : `" | "` — justification (DOD)

Le task file demandait de trancher à l'implémentation et de justifier. Les trois
candidats, mesurés à l'aune de la contrainte qui tranche — *le lecteur doit
pouvoir distinguer une valeur de son intervalle de référence sans ambiguïté* :

| Candidat | Verdict |
|---|---|
| Tabulation (`\t`) | **écarté** — le PDF est rendu en police proportionnelle (QuestPDF, Lato) ; une tabulation n'y aligne aucune colonne et se dessine comme un blanc de largeur arbitraire. Elle *déplace* l'ambiguïté au lieu de la lever. |
| Plusieurs espaces | **écarté** — visuellement indistinguable d'un espace unique après rendu, et un lecteur ne peut pas décider si `7,2  g/dL` est une cellule ou deux. |
| **Barre verticale ` \| `** | **retenu** — visible en toutes circonstances, indépendant de la police et de la largeur de colonne. Coût assumé : un caractère ajouté au contenu clinique restitué. |

Le coût est accepté parce que l'alternative est une restitution *mal
interprétable* : le défaut d'origine ne rendait pas la lecture pénible, il la
rendait **fausse** (`Hémoglobine7,2g/dL13,0-17,0` se lit tout aussi bien comme
une hémoglobine à 7,2 qu'à 7,213). Sur un document versé au dossier patient, un
caractère de ponctuation en trop est préférable à une valeur ambiguë.

### Trois effets de bord traités avec le séparateur

Séparer les cellules seules aurait laissé le tableau illisible pour trois
raisons voisines, toutes corrigées dans la même passe :

1. **Indentation de source** — les blancs entre deux rangées ou sections
   (`TABLE`/`THEAD`/`TBODY`/`TFOOT`) étaient émis tels quels, ce qui indentait
   chaque rangée d'un tableau formaté lisiblement à la source.
2. **Collage au texte environnant** — un tableau tombait dans le `default:` sans
   saut de ligne : sa première cellule se lisait comme la fin de la phrase
   précédente.
3. **Rangée entièrement vide** — sans garde, elle aurait rendu des séparateurs
   nus (` | | | `).

### Chemin CDA (DOD, point 4)

Aucun code supplémentaire : `RenderMedicalDocumentBody` appelle **le même**
`HtmlToPlainText` en repli quand la colonne Markdown d'un document CDA r2 est
vide. La correction couvre donc les deux chemins, et un test le prouve
(`BuildPdfWithMedicalDocumentHtmlTableSeparatesCells`). Quand la colonne
Markdown est renseignée, c'est `MarkdownPdfRenderer` qui rend un vrai tableau —
chemin distinct, non concerné.

### Le garde-fou sync-IO n'était pas celui qu'on croyait

Le task file demandait que les tests d'intégration `/print` et `/export/pdf`
tournent **contre un flux refusant les écritures synchrones**, et non un
`MemoryStream` permissif. L'hypothèse naturelle — « un TestServer refuse déjà
les écritures synchrones, `AllowSynchronousIO` valant `false` par défaut » — est
**fausse** : vérifiée le 2026-09-08 par une route sonde qui écrit en synchrone
dans `Response.Body`, elle est passée **sans lever**. S'appuyer dessus aurait
produit un garde-fou de façade — précisément le travers que cette task corrige
chez les tests PDF sur `MemoryStream`.

Le refus est donc posé explicitement : un décorateur de flux
(`ThrowOnSynchronousWriteStream`) installé par middleware sur toutes les routes
du harnais, qui reproduit le comportement de Kestrel. Deux tests le prouvent
(l'un sur le décorateur, l'autre sur la route sonde → 500).

**Et le garde-fou a été vérifié en réinjectant la régression** : en remplaçant
le `FileBufferingWriteStream` + `DrainBufferAsync` de task-077 par une écriture
directe dans `output`, les deux tests d'endpoint passent au rouge. Le correctif
d'origine a ensuite été restauré à l'identique (diff vide).

## Timings

*(généré par `tools/timing/report.sh --task task-190 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 1 min 25 s | — | — | — | — |
| **Total cycle** | | **1 min 25 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |

## Branches

Nom de branche unique : `fix/task-190-print-table-cell-separators` (préfixe `fix/` —
défaut de lisibilité, pas une nouvelle fonctionnalité).

- `api-mail` (pushed) : `fix/task-190-print-table-cell-separators` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-190-print-table-cell-separators
- `dtos-mss` (pushed, auto-inclus) : `fix/task-190-print-table-cell-separators` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-190-print-table-cell-separators
  — branche créée proactivement (règle d'auto-inclusion CLAUDE.md). Aucun changement
  de contrat attendu pour cette US : si elle reste sans commit, aucune PR ne sera ouverte.

Pré-flight du 2026-09-08 : les 7 repos automatisés sur `develop`. Premier essai
refusé (api-mail et dtos-mss encore sur `fix/task-194-…`, PR #223 en attente de
merge) — relance verte après checkout `develop`.
