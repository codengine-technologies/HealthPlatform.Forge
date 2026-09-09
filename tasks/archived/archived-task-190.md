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

### Passe qualité `/simplify` — ce qui a été appliqué

Reuse, simplification, efficacité, altitude. Appliqué : promotion du décorateur
anti-écriture-synchrone dans `mss.mail.testing.shared` (il existait **en deux
exemplaires** pour le même garde-fou task-077), docs ramenées à ce que fait le
code, garde de rangée vide simplifiée (`TrueForAll` est déjà vrai sur une liste
vide), prédicat hissé hors de boucle, `TagName` évalué une fois,
`IsTableStructure` renommé `IgnoresInterElementWhitespace`, second `Regex` hissé
comme le premier. Détail dans le message de commit `e33d99a1`.

### Découvertes de la passe qualité — à ne pas perdre

**1. Un test de garde sync-IO existait déjà, et la task l'ignorait.**
`MailExportControllerTests.PdfResponseWhenSynchronousIoIsDisallowedWritesAllBytesAsync`
(api.tests) exerce **déjà** `/print` et `/export/pdf` contre un flux refusant
les écritures synchrones. La section « Ce qui est conservé du périmètre
d'origine » affirmait qu'« aucun test du repo n'exerce ces deux routes de bout
en bout » : c'est vrai **au sens HTTP/DI** (ce test appelle l'action
directement sur un `DefaultHttpContext`, avec `IMailExportService` substitué,
donc sans QuestPDF, sans routage, sans MVC), mais faux au sens « le piège
task-077 n'est pas gardé ». Les nouveaux tests d'intégration gardent ce que
l'ancien ne pouvait pas voir — le vrai service à travers le vrai pipeline — et
les deux se complètent. **Même travers que celui documenté en tête de cette
task** : un constat posé sans lire le code existant.

**2. La plateforme a un second convertisseur HTML→texte, et il sépare déjà les
cellules avec le même séparateur.**
`Interop.Cda.Helpers.HtmlToTextHelper.ConvertHtmlToPlainText`
(`interop/src/Interop.Cda/Helpers/HtmlToTextHelper.cs`, livré par le NuGet
`Interop.Cda.Parser` 93.0.0) est appelé par `EmailSummaryService.cs:165` et
`ImapService.cs:4357`. Il traite `td`/`th` en ajoutant `" | "` — **exactement le
séparateur retenu ici**, choisi indépendamment. Deux conséquences :

- le choix du séparateur est **cohérent avec la plateforme**, argument plus
  fort que le raisonnement a priori consigné plus haut ;
- il y a bien **deux** implémentations de « HTML de mail → texte lisible » dans
  cet assembly, aux règles de mise en forme divergentes (puces `• ` ici,
  troncature à 10 000 caractères là, jeux de balises différents). Les unifier
  est un vrai gain d'altitude, **hors périmètre** : ce sont des chemins
  distincts (impression vs résumé IA / corps IMAP), le helper est porté par un
  NuGet, et l'unification changerait la sortie d'impression de tout mail HTML.
  Candidat pour une task dédiée.

### Pistes écartées, avec leur motif — ne pas les re-litiger

| Piste | Motif de l'écart |
|---|---|
| Utiliser une facilité de rendu texte d'AngleSharp au lieu du walker maison | **Elle n'existe pas.** AngleSharp 1.5 n'expose que des `IMarkupFormatter` (émetteurs de *balisage*) ; pas d'`innerText`, pas de rendu texte conscient de la mise en page. Un formatter custom serait le même switch par balise avec *moins* de contexte (il ne sait pas qu'il est dans un `TR`). |
| Rendre de vrais tableaux QuestPDF (comme `MarkdownPdfRenderer.RenderTable`) | **Refonte de mise en page**, explicitement hors scope (§ Hors scope). Le chemin HTML aplatit tout le corps en un seul `.Text(string)` ; en sortir change l'impression de **tout** mail HTML et invalide les assertions de texte PDF existantes, dans un repo sans stratégie de PDF de référence (cf. le `[ExcludeFromCodeCoverage]` de `MarkdownPdfRenderer`, task-032bis). |
| Généraliser la règle du blanc insignifiant (contexte de bloc) à `UL`/`DIV`/`DL` | Correct sur le fond, mais **change la sortie du HTML indenté non-tabulaire**, au-delà du symptôme rapporté, et aucun test ne la fixe aujourd'hui. Le concept est **nommé** (`IgnoresInterElementWhitespace`) sans être élargi : la généralisation est un commit à part. |
| Remplacer `RecordingAuditService` par `Substitute.For<IAuditService>()` + `Received(1)` | L'idiome courant du repo n'**exécute pas** la lambda de peuplement de la trace : une exception dedans passerait inaperçue. Ici elle est exécutée sur un vrai `MailDto`. Motif consigné dans le doc de la classe. |
| Supprimer `BuildPdfWithMedicalDocumentHtmlTableSeparatesCells` (produit de deux tests existants) | C'est la **preuve du point 4 du DOD** (chemin CDA). La retirer retirerait une couverture exigée. |
| Passer les deux `Regex` en `[GeneratedRegex]` | Exigerait de rendre `MailExportService` `partial` pour un `\s+` évalué une fois par mail exporté. Les deux sont hissés en `static readonly`, ce qui règle CA1869. |

## Sonar log

Analyse complète du 2026-09-08 sur la branche `fix/task-190-print-table-cell-separators`
(projet `healthplatform-api-mail`, SonarQube 25.6). Build Release + 5 suites avec
couverture OpenCover, puis scan. Rapport traité côté serveur (`SUCCESS`).

### KPIs

| Métrique | Valeur | Cible | Verdict |
|---|---|---|---|
| Bugs | 2 | 0 | hérités (bench k6) |
| Vulnerabilities | 0 | 0 | ✅ |
| Security Hotspots | 15 (dont 12 `TO_REVIEW` en new code) | 0 `TO_REVIEW` | hérités (bench k6 + Dockerfile) |
| Code Smells | 72 | — | hérités |
| Coverage | 88,2 % | ≥ 95 % (long terme) | inchangé |
| New coverage | **88,3 %** | ≥ 80 % | ✅ |
| Duplication | 0,3 % | < 3 % | ✅ |
| Reliability rating | C | A | hérité (les 2 bugs) |
| Security rating | **A** | A | ✅ |
| Maintainability rating | **A** | A | ✅ |
| Lignes de code | 50 744 | — | — |

**Quality Gate : ERROR — intégralement hérité.**
Deux conditions rouges, `new_violations = 72` et
`new_security_hotspots_reviewed = 0 %`.

### Phase 1 (new code) — zéro dette introduite

**Aucun des 72 findings ni des 12 hotspots ne touche un fichier de task-190.**
Vérifié par regroupement par fichier des issues `inNewCodePeriod=true` : les six
fichiers écrits ou modifiés par cette task (`MailExportService.cs`,
`MailExportControllerIntegrationTests.cs`, `MailExportHtmlToPlainTextTests.cs`,
`MailExportServiceTests.cs`, `MailExportControllerTests.cs`, `AsyncOnlyStream.cs`)
n'apparaissent **pas une seule fois**. Rien à corriger, donc aucune itération
de fix.

Répartition réelle des 72 : `tests/loadtest-k6/` **46** (report.py 23,
journey-model.js 14, journey.js 9), reste dispersé sur des services
d'embedding, repositories et sessions IMAP — tous issus de tasks **déjà
mergées**. Les 2 bugs : `python:S3923` dans `test_report_pinned_palier.py:68` et
`python:S1244` dans `report.py:2661`.

**C'est exactement le piège déjà documenté** : la new-code period de ce projet
est en mode `PREVIOUS_VERSION` avec une baseline au **2026-04-17**, soit près de
cinq mois de travail mergé considéré comme « nouveau ». Un Quality Gate ERROR
n'y vaut donc **pas** preuve de dette introduite par la task courante, et le
vérifier fichier par fichier est obligatoire avant de conclure quoi que ce soit.

Corollaire positif : zéro finding sur du code C# frais signifie que
`conventions/csharp.md` a bien été appliqué d'emblée (CA1861, CA1869, CA1859,
S3267 notamment) — aucune entrée à créer ni compteur à incrémenter.

### Phase 2 (dette héritée) — skippée, motivée

Best-effort et optionnelle par construction (`agents/sonar.md`). Skippée ici
parce que la totalité des findings vit dans des fichiers **hors périmètre** de
cette US : les traiter violerait la règle 6 (scopes isolés) et la règle 5
(hygiène de PR) en mêlant un correctif de lisibilité PDF à un nettoyage du banc
de charge k6. La dette du bench mérite sa propre task — c'est là qu'elle sera
visible et revue.

### Deux erreurs de documentation corrigées au passage

1. **Le port de SonarQube est 9001, pas 9000.** `agents/sonar.md` portait un
   encadré « Corrigé le 2026-08-30 » affirmant que « le port annoncé était 9001
   (le serveur répond sur 9000) ». C'est l'inverse : `docker port sonarqube`
   donne `9000/tcp -> 0.0.0.0:9001`, et `curl` sur 9000 ne répond pas
   (`000`) là où 9001 rend `200`. La « correction » avait donc remplacé une
   valeur juste par une fausse — dans le même encadré qui déplore qu'une valeur
   fausse « a coûté une analyse ratée ». Corrigé.
2. **`SONAR_PROJECT_KEY` du `.env` workspace vaut `healthplatform`**, un projet
   qui existe mais n'est plus analysé (dernière analyse 2026-09-02) et n'est pas
   celui d'api-mail. La bonne clé est `healthplatform-api-mail` (analysé le
   jour même). `agents/sonar.md` le disait déjà ; le `.env` le contredisait.
   Surchargé explicitement dans les commandes du run.

## PRs

- `api-mail` (pushed) : **[PR #224](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/224)** — label `awaiting-human-merge`
- `dtos-mss` (pushed, auto-inclus) : **aucune PR** — branche créée proactivement
  par la règle d'auto-inclusion, aucun changement de contrat nécessaire, donc
  zéro commit. Branche à supprimer au `/merge`.
- `client-angular`, `client-mobile` : non listés (US backend-only justifiée) —
  aucune intervention.

## Code Review Summary

**Deux blocages trouvés et corrigés**, tous deux reproduits avant correction.
La revue portait sur l'axe **correction**, celui que la passe qualité
`/simplify` exclut par construction — c'est précisément là que les défauts
étaient.

1. **Régression introduite par le premier commit** : un tableau imbriqué dans
   une cellule voyait ses rangées aplaties sur une seule ligne
   (`13,0-17,0 Hématies` lu comme un seul champ). Avant le correctif, la même
   entrée produisait **deux lignes** — on échangeait donc une ambiguïté contre
   une pire, sur la **forme dominante du mail HTML réel** (tableau de mise en
   page enveloppant le tableau de résultats). Aucun test initial ne la voyait :
   tous portaient sur un tableau de premier niveau.
2. **Sonde sync-IO verte en local, rouge en CI** : le harnais ne monte aucun
   gestionnaire d'exceptions, donc seul le `DeveloperExceptionPage` — ajouté
   uniquement si `IsDevelopment()` — convertissait l'exception en 500. La CI ne
   fixe aucune variable d'environnement. Mon poste exporte `Development` : le
   run local validait l'assertion **pour la mauvaise raison**. Environnement
   épinglé à `Production`, assertion portée sur l'exception, suite complète
   rejouée sous `Production`.

Deux défauts de la même classe corrigés au passage (`<caption>` collée à la
première cellule ; séparateur nu sur cellule de bord vide), et une garde
existante d'`api.tests` — affaiblie par la mise en commun du décorateur —
restaurée en suivant la libération du flux.

**Trois limites assumées épinglées par des tests** pour rester des décisions :
`rowspan`/`colspan` non honorés, barre verticale déjà présente dans le contenu,
aplatissement de la structure interne d'une cellule.

**Suggestion hors scope** : deux convertisseurs HTML→texte coexistent dans la
plateforme aux règles divergentes. **Défaut pré-existant relevé** :
`AppendNodeText` récurse sans plafond de profondeur (débordement de pile
possible sur HTML de mail très imbriqué) — mérite sa propre task.

### Leçon de méthode

Les deux blocages partagent une cause : **une validation locale verte prouvée
insuffisante**. Le premier parce que les tests ne couvraient qu'une forme
d'entrée ; le second parce que l'environnement local différait de la CI. Le vert
local n'est pas le vert de la CI, et un test qui passe ne dit pas qu'il garde
quelque chose — c'est le même enseignement que le garde-fou sync-IO de cette
task, appliqué à la task elle-même.

## Timings

*(généré par `tools/timing/report.sh --task task-190 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 1 min 25 s | — | — | — | — |
| /develop | ok | 33 min 31 s | 3 (48 s) | 9 (6 min 31 s) | — | api-mail 3B/9T |
| /sonar | ok | 9 min 28 s | 1 (17 s) | 1 (1 min 59 s) | 1 (1 min 39 s) | api-mail 1B/1T, Phase 1 clean (0 finding sur les fichiers task-190); Phase 2 skippee (dette heritee hors perimetre) |
| /lint-angular | skipped | 14 s | — | — | — | client-angular non touche par task-190 (Repos: api-mail, Single frontend: true); 2 environment.ts modifies = WIP humain pre-existant sur feature/nova-rewriting-mss, non touches |
| /lint-mobile | skipped | 2.7 s | — | — | — | client-mobile non touche par task-190 (Repos: api-mail); repo sur develop, arbre propre |
| /verify-visual | skipped | 2.3 s | — | — | — | aucun ecran client-mobile touche (Repos: api-mail, pas de Stitch design log); US backend-only |
| /review | ok | 29 min 33 s | 2 (20 s) | 2 (3 min 52 s) | — | api-mail 2B/2T, PR #224 ouverte, awaiting-human-merge; 2 blocages trouves en revue et corriges |
| /tech-writer | ok | 4 min 50 s | — | — | — | — |
| **Total cycle** | | **1 h 19 min** | **6 (1 min 26 s)** | **12 (12 min 22 s)** | **1 (1 min 39 s)** | |

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

## Merged

Mergé le **2026-09-09** par l'humain (HAG, règle 10 — `/merge task-190 --i-tested`).

| Repo | PR | Commit squash sur `develop` |
|---|---|---|
| `api-mail` | [#224](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/224) — squash-merged | `7aa0551` — *fix(mail): séparer les cellules des tableaux imprimés (lisibilité clinique) — task-190 (#224)* |
| `dtos-mss` | aucune PR — branche auto-incluse restée sans commit | — |

- Branches distantes `fix/task-190-print-table-cell-separators` supprimées sur
  `api-mail` et `dtos-mss` ; **branches locales conservées** (inspection
  rétroactive).
- `client-angular` / `client-mobile` : non listés (US backend-only) — aucune
  intervention.
- Staging : `forge/staging-task-292-294-20260908` **conservée** — hors de la
  plage de cette task (190 ∉ [292, 294]), elle appartient à un autre run.
- CI `develop` (api-mail) : CI_PLACEHOLDER
