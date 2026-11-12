# todo-task-449.md — Recherche : suggestions pendant la frappe, patients et messages

**Repos**: api-mail, dtos-mss, client-angular
**Reprises**: 7
**Dependencies**: done-task-442 (formulaire), done-task-446 (patients trouvés, vue « Mails du patient » depuis les
résultats)
**Epic**: E023
**Priorité**: EPIC E023, demandée par l'humain le 2026-11-10. Une seule barre pour trouver un patient ou un message :
le médecin tape quelques lettres, choisit, et la recherche est faite. **Complétée par l'humain le 2026-11-11** :
préfixes de critère (`de :`, `à :`, `patient :`, `type :`, `objet :`) et recherche exacte entre guillemets.

> **Origine.** Analyse du 2026-11-10 (suggestions par catégorie d'Apple Mail et d'Outlook, étiquettes dans la barre).
> Décision de l'humain : point d'entrée unique patients et messages ; l'historique sort du formulaire et devient une
> catégorie de suggestions.

## Ce qui est établi

- `GET /api/v1/Search/suggestions` rend une liste figée de termes médicaux courants (`GetCommonMedicalTermSuggestions`),
  sans lien avec la boîte, et n'est pas tracé (`TraceExempt`).
- L'historique des recherches (task-119) est affiché en tête de la fenêtre de critères.
- La recherche de patients a son propre écran.

## Objective

Pendant la frappe, la barre de recherche propose, par catégories, ce que la boîte contient ; un choix devient une
étiquette de critère ou ouvre directement le patient.

Règles :
- **Champ vide** (au focus) : la catégorie **« Recherches récentes »** (les 5 dernières de la personne), à la place de
  l'historique dans le formulaire.
- **À partir de 2 caractères**, après une courte pause de frappe, quatre catégories, dans cet ordre, chacune limitée à
  5 entrées, une catégorie vide n'est pas affichée :
  1. **Patients** : patients de la boîte dont le nom de naissance, le nom d'utilisation ou le prénom **commence par** les
     lettres tapées (insensible à la casse et aux accents ; jamais phonétique ni approché). Affichage : nom de
     naissance, prénom, date de naissance, sexe, « INS qualifiée » le cas échéant ; jamais l'INS.
  2. **Correspondants** : expéditeurs et destinataires de la boîte dont le nom ou l'adresse commence par les lettres.
  3. **Types de document** : types de document médical dont le libellé contient les lettres (« Compte rendu
     d'hospitalisation », « Biologie »…).
  4. **Recherches récentes** dont le texte contient les lettres.
- **Choisir** :
  - un **patient** ouvre la vue « Mails du patient » ;
  - un **correspondant** ou un **type de document** ajoute une **étiquette de critère** dans la barre
    (« De : Laboratoire Cerballiance », « Type : Biologie ») et lance la recherche ;
  - une **recherche récente** la rejoue.
- **Entrée** sans choisir de suggestion lance la recherche plein texte sur le texte tapé (sauf préfixe ou guillemets,
  voir ci-dessous).
- **Préfixes de critère** (ajout de l'humain du 2026-11-11). Reconnus en tête de saisie, insensibles à la casse et aux
  accents, avec ou sans espaces autour des deux-points (`de :paul`, `De: paul`, `de : paul`) :

  | Préfixe | Suggestions proposées (seule catégorie affichée) | Critère posé à Entrée sans choisir |
  |---|---|---|
  | `de :` | Correspondants **expéditeurs** dont le nom ou l'adresse commence par le texte | « De » contient le texte (`FromName` / `FromAddress`) |
  | `à :` (ou `a :`) | Correspondants **destinataires** dont le nom ou l'adresse commence par le texte | « À / Cc » contient le texte (`RecipientAddress`) |
  | `patient :` | Patients (mêmes règles que la catégorie « Patients ») | aucun : un patient **se choisit**, jamais une saisie libre (task-443) ; Entrée sans choix ne lance rien et laisse la liste ouverte |
  | `type :` | Types de document dont le libellé contient le texte | aucun : un type se choisit dans la nomenclature ; Entrée sans choix ne lance rien |
  | `objet :` | aucune | « Objet » contient le texte (`Subject`) |

  - Choisir une suggestion pose l'étiquette (« De : Paul MARTIN ») et lance la recherche, comme sans préfixe.
  - Le texte après un préfixe n'est **jamais** lu comme une identité de patient (patients trouvés de task-444), sauf
    avec `patient :`, ni cherché en plein texte dans les autres champs.
  - Un mot suivi de deux-points qui n'est pas un préfixe reconnu (`tension : 14/8`) est du texte ordinaire : recherche
    plein texte habituelle.
  - Un préfixe peut précéder une expression entre guillemets : `de : "Paul Martin"` → « De » contient exactement
    « Paul Martin » (casse ignorée).
  - Plusieurs critères se combinent : chaque étiquette posée reste dans la barre, et le texte restant est cherché en
    plein texte.
- **Recherche exacte entre guillemets** (ajout de l'humain du 2026-11-11). Une saisie qui contient au moins une
  expression entre guillemets droits (`"…"`) ou typographiques (`« … »`, `“…”`) déclenche une recherche **plein texte
  exacte, sans recherche sémantique** :
  - chaque expression entre guillemets doit figurer **telle quelle** dans le message : mêmes mots, consécutifs, dans le
    même ordre, commençant et finissant sur une frontière de mot (`"dernier résultat"` ne trouve pas « derniers
    résultats ») ;
  - **seule la casse est ignorée** : les accents et la ponctuation comptent (`"dernier résultat du 22/05/2026"` trouve
    « Dernier RÉSULTAT du 22/05/2026 », pas « dernier resultat du 22-05-2026 ») ; une suite d'espaces ou un retour à la
    ligne valent une espace ;
  - champs cherchés : ceux du plein texte (objet, corps, documents médicaux, expéditeur, noms de pièces jointes) ;
  - les mots hors guillemets de la même saisie sont **aussi obligatoires** (`"dernier résultat" potassium` : les deux) ;
    il n'y a ni groupe « une partie des mots » ni section « Résultats proches » ;
  - le serveur n'appelle **jamais** le fournisseur d'embeddings pour une telle saisie ;
  - la réponse enrichie de task-444 s'applique : l'endroit trouvé et un extrait dont la position couvre l'expression
    entière ;
  - un guillemet sans fermant est un caractère ordinaire : recherche habituelle ;
  - les guillemets et leur contenu sont rejoués tels quels par l'historique.
- Clavier : flèches pour parcourir, Entrée pour choisir, Échap pour fermer.
- Les suggestions sont celles de la **base de la boîte** : titulaire, délégataire et membre voient les mêmes patients et
  correspondants (règle 14), et leurs **propres** recherches récentes (l'historique appartient à la personne).
- **Une saisie de la forme d'une INS** ne produit aucune suggestion de patient et n'entre pas dans les recherches
  récentes (task-444).
- Délai : les suggestions apparaissent en moins de 300 ms au p95 sur la boîte cible de 10 000 messages.

### Hors périmètre

- Le mobile : task-451.
- La recherche en langage naturel : hors lot.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`, `HealthPlatform.Dtos.Mss.csproj`, weda2 (`nx build weda2`)
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`, `nx test weda2`, `nx test mss-lib`
- [ ] Tests unitaires du service de suggestions : chaque catégorie, préfixe insensible aux accents et à la casse, aucune
      correspondance approchée, limite par catégorie, saisie INS (≥ 1 test par branche)
- [ ] **Tests d'intégration de bout en bout (règle 1b)** sur la route de suggestions, sur le corpus fictif, lus dans la
      réponse réelle, chacun vu rouge par mutation :
      - `bern` : Catherine BERNARD dans « Patients », sans INS ; `bernart` : aucun patient ;
      - `cerb` : le laboratoire du corpus dans « Correspondants » ;
      - `bio` : « Biologie » dans « Types de document » ;
      - **règle 14** : deux personnes rattachées à la même boîte reçoivent les mêmes patients et correspondants, et
        chacune ses propres recherches récentes ;
      - **cas d'échec** : moins de 2 caractères → 400 en `ProblemDetails` ; boîte sans verdict de l'opérateur → refus
- [ ] **Préfixes** — tests d'intégration de bout en bout sur la route de suggestions et sur
      `POST /api/v1/Search/semantic`, lus dans la réponse réelle, chacun vu rouge par mutation :
      - `de : paul` : seuls des correspondants expéditeurs commençant par « paul » ; aucun patient ;
      - `de : paul` puis Entrée sans choix : seuls les messages dont l'expéditeur contient « paul » (un message citant
        « Paul » dans son corps n'est **pas** rendu) ; aucun patient trouvé ;
      - `objet : bilan` : seuls les messages dont l'objet contient « bilan » ;
      - `tension : 14/8` : recherche plein texte habituelle
- [ ] **Guillemets** — tests d'intégration de bout en bout sur `POST /api/v1/Search/semantic`, lus dans la réponse réelle,
      chacun vu rouge par mutation :
      - `"dernier résultat du 22/05/2026"` trouve le message qui contient « Dernier RÉSULTAT du 22/05/2026 » (casse
        différente), pas celui qui contient « dernier resultat du 22-05-2026 » ni « derniers résultats du 22/05/2026 » ;
      - le générateur d'embeddings **n'est pas appelé** (double qui échoue s'il l'est) et aucun hit n'est `Similar` ;
      - `"dernier résultat" potassium` : seul le message qui contient les deux ;
      - l'extrait (task-444) porte une position qui couvre l'expression entière ;
      - un guillemet non fermé : recherche habituelle
- [ ] Tests unitaires de l'analyse de la saisie : chaque préfixe (variantes d'espaces, de casse, d'accent), préfixe
      inconnu, expressions entre guillemets droits et typographiques, guillemet non fermé, mélange guillemets + mots
- [ ] Mesure consignée dans le `## Develop log` : p95 d'une recherche entre guillemets sur la boîte de 11 178 messages,
      comparé à la recherche plein texte habituelle (l'index trigramme sur texte normalisé peut présélectionner, la
      vérification exacte se fait sur le texte d'origine)
- [ ] La route de suggestions n'est plus `TraceExempt` : elle révèle des identités de patients, et chaque appel qui rend
      au moins un patient est tracé comme une consultation (famille `HealthDataAccess`), au nom de la personne réelle
- [ ] Mesure consignée dans le `## Develop log` : p95 des suggestions sur la boîte de 11 178 messages, < 300 ms
- [ ] Contrat `dtos-mss` publié (la route existante peut être remplacée ; aucun autre consommateur que weda2 et le
      mobile) et consommateurs .NET mis à jour ; types TypeScript de weda2 alignés
- [ ] Tests de composant weda2 : catégories et ordre, recherches récentes au focus, choix d'un patient (vue « Mails du
      patient »), choix d'un correspondant (étiquette + recherche), navigation au clavier, historique retiré du
      formulaire ; chacun vu rouge par mutation
- [ ] **Scénario e2e** `E2E-SEARCH-013` v1 : « Trouver un patient en tapant les premières lettres de son nom » — attendu :
      `bern` propose Catherine BERNARD, et la choisir ouvre ses messages. Clients : angular requis, mobile requis avec
      **divergence temporaire** (raison : « les suggestions arrivent sur le mobile avec la refonte mobile », tache :
      task-451). Implémenté dans weda2, vu rouge par mutation
- [ ] **Scénario e2e** `E2E-SEARCH-014` v1 : « Restreindre la recherche à un expéditeur en tapant « de : » » — attendu :
      `de : ` suivi des premières lettres d'un correspondant ne propose que des correspondants ; le choisir pose
      l'étiquette « De : … » et ne rend que ses messages. Clients : angular requis, mobile requis avec **divergence
      temporaire** (raison : « les préfixes arrivent sur le mobile avec la refonte mobile », task : task-451). Implémenté
      dans weda2, vu rouge par mutation
- [ ] `data-testid` sur chaque élément interactif ajouté
- [ ] Aucune donnée de santé en clair dans les logs (lettres tapées, noms, INS)
- [ ] client-angular : code-only, aucun commit
- [ ] **Prévention (règle d'or)** : consigne dans `conventions/csharp.md` : une route qui rend une identité de patient
      n'est jamais `TraceExempt`

## Manual Test Plan

1. Lancer le backend sur le corpus fictif : `cd Api/Mail/src/AppHost && dotnet run`, puis le seed de référence. Lancer
   weda2 : `cd Client/Angular/front && npm start`.
2. Cliquer dans la barre, champ vide : « Recherches récentes » s'affiche ; la fenêtre de critères ne montre plus
   l'historique.
3. Taper `bern` : « Patients » propose Catherine BERNARD (date de naissance, sans INS). La choisir : ses messages
   s'affichent dans la vue « Mails du patient ».
4. Taper `cerb` : « Correspondants » propose le laboratoire ; le choisir : l'étiquette « De : … » apparaît, la recherche
   est lancée.
5. Taper `bio` : « Types de document » propose « Biologie ».
6. Parcourir les suggestions au clavier (flèches, Entrée, Échap).
7. Taper `de : ` puis les premières lettres d'un correspondant : seuls des correspondants sont proposés ; en choisir un
   pose l'étiquette « De : … » et ne rend que ses messages. Recommencer avec `de : paul` puis Entrée sans choisir : les
   messages dont l'expéditeur contient « paul », et pas ceux qui citent Paul dans leur corps.
8. Taper `objet : bilan` puis Entrée : seuls les messages dont l'objet contient « bilan ».
9. Taper `"dernier résultat du 22/05/2026"` (avec les guillemets) puis Entrée : seuls les messages qui contiennent
   exactement cette expression, casse ignorée ; aucune section « Résultats proches ». Sans les guillemets, la même saisie
   rend aussi des messages qui n'en contiennent qu'une partie.
10. Ouvrir le journal de la boîte : la saisie `bern` y figure comme consultation, au nom de la personne, sans les lettres
   tapées.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du praticien)
- **Vague Ségur** : hors Ségur — ergonomie de la recherche
- **Exigences DSR honorées** : non applicable
- **INS** : jamais affichée ni suggérée ; une saisie de forme INS ne produit aucune suggestion et n'est pas mémorisée ;
  seul le statut « INS qualifiée » est montré
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : verdict de l'opérateur MSSanté requis (règle 14) ; mêmes patients et correspondants pour toutes les
  personnes de la boîte ; recherches récentes propres à chaque personne (donnée de la personne)
- **Interop CI-SIS** : types de document lus dans la nomenclature déjà portée par la plateforme (types de document des
  volets CI-SIS) ; aucun nouvel échange
- **Tracé PGSSI-S** : chaque appel qui révèle au moins un patient est tracé comme consultation (`HealthDataAccess`), au
  nom de la personne réelle, avec son rôle, 3 653 jours ; les lettres tapées ne sont pas tracées
- **Consentement patient** : non applicable
- **Référentiels métier** : types de document médical (LOINC des volets CI-SIS, déjà en place) ; aucun nouveau
- **Hébergement HDS** : oui — base de la boîte ; les recherches récentes restent dans le cache distribué existant
- **AIPD / impact RGPD** : à vérifier — les suggestions exposent des identités de patients pendant la frappe ; même
  périmètre de personnes habilitées

## Branches

- `api-mail` (pushed) : feat/task-449-recherche-suggestions-pendant-la-frappe — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-449-recherche-suggestions-pendant-la-frappe
- `dtos-mss` (paresseuse) : créée par `/develop` au premier changement de contrat (même nom).
- `client-angular` (code-only) : la forge écrit sur la branche checked out dans `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`) — humain gère branche, commit, push, PR TFS

## Develop log

**Ordre** : dtos-mss → api-mail → client-angular (code-only, `feature/nova-mss-weda-integration`, aucun commit).

### dtos-mss (branche paresseuse `feat/task-449-recherche-suggestions-pendant-la-frappe`, publié **600**)

- `SearchSuggestionsResponseDto` (`Prefix`, `Text`, `Patients`, `Correspondents`, `DocumentTypes`, `RecentSearches` ;
  `MaxPerCategory` 5, `MinQueryLength` 2), `SearchInputPrefix`, `SearchCorrespondentDto` / `SearchCorrespondentRole`,
  `SearchDocumentTypeDto`. Types nouveaux seulement ; le patient suggéré réutilise `SearchFoundPatientDto` (sans INS).
  Consommateur .NET : api-mail bumpé (`cf8d018c`).

### api-mail

- **Saisie** (`SearchInput`, `SearchPhrases`) : préfixe en tête (`de`, `à`/`a`, `patient`, `type`, `objet`), casse,
  accents et espaces autour des deux-points ignorés ; un mot suivi de deux-points qui n'est pas un préfixe est du
  texte. Un préfixe prend tout le reste, ou l'expression entre guillemets qui l'ouvre. Guillemets droits ou
  typographiques ; un guillemet non fermé est ordinaire.
- **Préfixes dans `POST /search/semantic`** : `de :` → « De contient » (`FromAddress`, qui lit nom et adresse), `à :` →
  `RecipientAddress`, `objet :` → `Subject`, le reste en plein texte ; `patient :` / `type :` → 400 (« se choisit dans
  la liste ») ; le texte d'un préfixe n'est jamais lu comme une identité (pas de patients trouvés).
- **Guillemets** : recherche exacte sans recherche par le sens (aucun appel au fournisseur d'embeddings, aucun
  `Similar`, pas de groupe « une partie des mots »). Les mots des expressions et les mots hors guillemets, tous requis,
  présélectionnent par l'index trigramme du texte normalisé ; chaque candidat est vérifié sur le texte d'origine
  (`SearchPhrases.Pattern` : mots consécutifs, frontières de mot, casse seule ignorée, espaces et retours à la ligne =
  une espace), **dans l'ordre de la recherche jusqu'à la page et un de plus**. Extrait : l'expression surlignée
  entière (`SearchExcerpts.AroundPhrases`, `SearchHitEnrichment.ApplyPhrases`).
- **`GET /search/suggestions?query=`** (`SearchSuggestionService`) : remplace la liste figée de termes. Patients
  (début de mot du nom ou du prénom, normalisé ; une saisie de forme INS n'en propose aucun), correspondants
  (expéditeurs puis destinataires, début de mot du nom ou de l'adresse), types de document (`MedicalDocumentTypeCatalog`,
  libellé qui contient les lettres), recherches récentes de la personne qui les contiennent ; 5 par catégorie ; un
  préfixe garde sa seule catégorie ; < 2 caractères après le préfixe → 400. **N'est plus `TraceExempt`** :
  `[TracedInCode(MailSearch)]`, le service trace chaque réponse qui nomme au moins un patient (famille
  `HealthDataAccess`), au nom de la personne, avec le nombre de patients, jamais les lettres.
- **Historique propre à la personne** (`SearchHistoryOwner`) : la clé nommait la boîte seule — titulaire, délégataire
  et membre lisaient les recherches les uns des autres. Elle nomme désormais la boîte et la personne (sujet
  d'authentification, sinon RPPS). Défaut antérieur, corrigé parce que la DoD le demande (règle 14).
- Projection patient unique (`SearchPatientCandidate.ToFoundPatient`) pour les patients trouvés et suggérés.

**Tests d'intégration** (règle 1b, vrai contrôleur, vrais services, PostgreSQL réel, vrai historique en mémoire, vrai
`AuditService`) — `SearchSuggestionsIntegrationTests`, `SearchPrefixesAndPhrasesIntegrationTests`,
`MailboxAccessLockIntegrationTests` :

| Comportement | Test | Preuve rouge |
|---|---|---|
| `bern` : Catherine BERNARD (date, sexe, « INS qualifiée »), sans INS dans le JSON ; `bernart` : personne | `Bern_SuggestsCatherineBernard_…` | S1 (nom approché à 4 lettres) |
| `cerb` : le laboratoire (expéditeur), puis le secrétariat (destinataire) | `Cerb_SuggestsTheLaboratory_…` | S2 (correspondants sans filtre) |
| `bio` : « Biologie » | `Bio_SuggestsTheBiologyDocumentType` | S3 (tous les types) |
| Règle 14 : mêmes patients et correspondants pour deux personnes, chacune ses recherches récentes | `TwoPeopleOfTheMailbox_…` | S4 (historique de la boîte) |
| < 2 caractères (`b`, `de : p`) → 400 `problem+json` | `FewerThanTwoCharacters_Is400ProblemJson` | S8 |
| Réponse qui nomme un patient tracée au nom de la personne, sans les lettres ; sans patient, pas de trace | `AnAnswerNamingAPatient_IsTraced…` | S5 (trace retirée), S6 (trace sans patient) |
| `de : paul` (suggestions) : seuls des expéditeurs, aucun patient même si un patient s'appelle PAUL | `FromPrefix_SuggestsOnlySenders…` | S2, S7 (préfixe sans catégorie) |
| Délégataire refusé par l'opérateur → 403 sur les suggestions ; le titulaire les obtient | `Delegate_RefusedAtRenewal_Gets403_OnSearchSuggestions_…` | rouge sur le code d'avant (service absent) |
| `de : paul` (recherche) : seul le message de Paul MARTIN, pas celui qui cite Paul ; aucun patient | `FromPrefix_ReturnsOnlyTheMailsWhoseSender…` | P1 (préfixe ignoré), P2 |
| `objet : bilan` : seul l'objet « Bilan lipidique » | `SubjectPrefix_…` | P1 |
| `tension : 14/8` : recherche plein texte habituelle | `AWordFollowedByAColonThatIsNoPrefix_…` | P2 (mot + deux-points pris pour un objet) |
| `patient : bern`, `type : bio` → 400 | `APatientOrATypeTypedAfterItsPrefix_Is400…` | P1, P2 |
| `"dernier résultat du 22/05/2026"` : casse différente trouvée ; sans accent, tirets, autres mots écartés ; aucun appel d'embeddings, aucun `Similar` | `AnExpressionBetweenQuotes_FindsItWhateverItsCase_…` | Q1 (vérification sautée), Q2 (en hybride) |
| L'extrait surligne l'expression entière, telle qu'écrite | `…_ItsExcerptHighlightsTheWholeExpression_…` | Q2, Q4 (surlignage mot à mot) |
| `"dernier résultat" potassium` : les deux requis | `AnExpressionAndAWord_BothAreRequired` | Q2, Q3 (mots hors guillemets facultatifs) |
| Pagination exacte : la page dit qu'il en reste, la suivante les rend ; page qui finit sur un lot de vérification | `…_IsReadPageByPage_…`, `…_APageEndingOnACheckBatch_StillSaysMoreExist` | Q1, Q6 (page sans « un de plus ») |
| Guillemet non fermé : recherche habituelle (résultats proches compris) | `AnUnclosedQuote_IsAnOrdinarySearch` | Q5 |

- Unitaires : `SearchInputTests` (33 : chaque préfixe, variantes d'espaces, de casse, d'accent, préfixe inconnu,
  guillemets droits et typographiques, non fermés, mélange, motif exact) ; `SearchSuggestionServiceTests` (19 : chaque
  catégorie, chaque préfixe, limite, INS, trace, recherches récentes de la personne) ; `SearchControllerTests` (3).
- Mutations P1–P2, Q1–Q6, S1–S8 : 17 rouges.

**Mesures** (`Docs/audits/findings/plans/20261112-task-449/`, `cost449.cs`, copie `srch_lab` de la boîte de formation,
11 291 messages, 56 patients, index trigrammes construits, 30 passages après chauffe, Release) :

| Mesure | p50 | p95 | Borne |
|---|---|---|---|
| Suggestions (patients + expéditeurs + destinataires + types), 10 saisies | 152 ms | **175 ms** | < 300 ms ✅ |
| Recherche exacte entre guillemets, page de 50, 5 expressions | 192 ms | **240 ms** | — |
| Même texte sans guillemets (plein texte habituel) | 160 ms | 195 ms | — |

- Première version : chaque candidat vérifié avant de paginer → p95 **2 099 ms** (« "compte rendu" » : des milliers de
  textes relus). Corrigé : vérification par lots de 100, dans l'ordre, jusqu'à la page et un de plus ; écart final
  +45 ms au p95.

### client-angular (weda2, code-only)

- `core/models/search-suggestions.model.ts`, `MssApiService.getSearchSuggestions` (réponse par catégories).
- `MailSearchSuggestions` (`features/mail/services/mail-search-suggestions.ts`) : champ vide → les 5 dernières
  recherches ; à partir de 2 caractères après le préfixe, après 250 ms, les catégories ; flèches qui bouclent ;
  `readSearchBar` / `mustChooseInTheList` (jumeaux du préfixe serveur).
- `MailSearchSuggestionsComponent` : catégories dans l'ordre, une catégorie vide masquée, patient affiché avec date,
  sexe, « INS qualifiée » (jamais l'INS) ; choix au `mousedown`.
- Barre (`MailSearchComponent`) : les suggestions **remplacent l'historique du formulaire** (composant
  `mail-search-history` retiré, plus utilisé) ; un patient ouvre « Mails du patient » sans lancer de recherche ; un
  expéditeur pose « De » (`fromAddresses`), un destinataire « À », un type le critère de type, puis la recherche est
  lancée sans les lettres tapées ; une recherche récente est rejouée ; Entrée sans choix lance le texte tel quel (le
  serveur lit le préfixe), sauf après `patient :` / `type :` ; Échap ferme.
- Tests de composant `mail-search.suggestions.spec.ts` (11) : mutations G1–G11 toutes rouges (ordre, récentes au
  focus, limite à 5, vue du patient, rôle du correspondant, type, boucle du clavier, patient tapé, deux caractères,
  lettres gardées, Entrée sur la désignation).
- **E2E** `E2E-SEARCH-013` v1 (« pat-t » → PAT-TROIS → « Mails du patient ») et `E2E-SEARCH-014` v1 (« de : luc » →
  seul Dr Luc Bernard → étiquette « De : … », son seul message) ; catalogue : angular requis, mobile en divergence
  task-451. Joués verts sur le banc ; mutations servies E3 (patient vers une autre route) et E4 (expéditeur posé en
  « À ») rouges, marqueurs vérifiés dans le bundle puis retirés. Le corpus e2e n'a pas de Catherine BERNARD : la fiche
  du seed (`PAT-TROIS`) tient ce rôle.
- `nx test mss-lib` 1 635 ✅, `nx test weda2` 2 683 ✅, `nx build weda2` ✅ ; ESLint 0 erreur sur les fichiers touchés
  (`mail-search.component.ts` dépasse déjà `max-lines`, avertissement existant).

### Reprise 1 après `/review` (2026-11-12) — B1, S2, S3, S8, S9, S10, S12

S4 à S7 et S11 restent en arbitrage humain (`## Code Review Summary`), hors de cette reprise.

| Constat | Correctif | Test | Preuve rouge |
|---|---|---|---|
| **B1** Après Échap, Entrée choisissait la suggestion désignée (patient ouvert, consultation tracée) | flèches et Entrée-sur-désignation liste ouverte seulement ; `closeDropdown()` → `forgetDesignation()` | `mail-search.suggestions.spec.ts` « après Échap… » | rouge sur le code d'avant (recherche lancée par le correspondant désigné) |
| **S2** Réponse du texte précédent affichée et désignable pendant la frappe | réponse taguée par son texte, affichée seulement pour le texte courant | « pendant la frappe… » | rouge sur le code d'avant |
| **S3** `distinctUntilChanged` laissait la liste vide (`bern`, `b`, `bern` en < 250 ms) | retiré | « retaper le même texte… » | rouge sur le code d'avant |
| **S8** Saisie des suggestions non bornée | 100 caractères au plus (400), 5 premiers mots cherchés | intégration `AQueryLongerThan100Characters_Is400ProblemJson` ; unitaire `OnlyTheFirstFiveWords_…` | rouge avant ; mutation R8 |
| **S9** Recherche exacte : jusqu'à 25 000 textes relus | `SearchLimits.ExactCandidatesCheckedMax` = 1 000 candidats vérifiés au plus ; au-delà, réponse tronquée | intégration `AnExpressionOfFrequentWords_StopsCheckingAtItsCap_…` (1 001 messages) | rouge avant ; mutation R9 |
| **S10** Personne inconnue → clé partagée de la boîte | `SearchHistoryOwner` rend une clé vide : ni enregistrement ni lecture | intégration `ARequestWithoutAKnownPerson_KeepsNoHistory_…` ; unitaires `SearchHistoryOwnerTests` | rouge avant ; mutation R10 |
| **S12** `--` rendait les 5 dernières recherches ; Redis en panne faisait échouer la réponse | 400 sans lettre ni chiffre ; historique indisponible → catégorie vide | intégration `FewerThanTwoCharacters_OrNoLetterNorDigit_…`, `TheHistoryUnavailable_EmptiesRecentSearchesOnly` | rouges avant ; mutations R12a, R12b |

- Test adapté : `SearchEnrichedResponseIntegrationTests.Semantic_CompleteIns_…` porte désormais une personne (une
  requête réelle en a toujours une) ; `SearchControllerTests` idem.
- weda2 : `nx test mss-lib` 1 638 ✅, `nx test weda2` 2 683 ✅, `nx build weda2` ✅, ESLint 0 erreur.
- **Prévention** : `conventions/angular.md` § `suggestions-de-saisie-choisies-visibles`.

### Reprise 2 après `/review` (2026-11-12) — B2, B3, S13, S14, S15 (weda2 seulement)

| Constat | Correctif | Test | Preuve rouge |
|---|---|---|---|
| **B2** Entrée dans « À / Cc », « Objet », « Nom de pièce jointe » choisissait la suggestion désignée de la barre | gestionnaire propre aux champs (`onFieldKeyDown` : Entrée = lancer ; flèches laissées au champ) | `mail-search.suggestions.spec.ts` « Entrée dans le champ « Objet »… » | rouge sur le code d'avant (patient ouvert) |
| **B3** Après Échap, « Fermer la recherche » ou un rejeu, les suggestions de l'ancien texte restaient désignables | `restoreCriteria` met les suggestions au texte restauré | « après Échap, la réouverture… » | rouge sur le code d'avant |
| **S13** « Voir plus » sans fin après le plafond de vérification exacte | une page suivante vide ne propose plus de suite (`MailSearchSession.loadMore`) | `mail-search-session.spec.ts` « une page suivante vide… » | rouge sur le code d'avant |
| **S14** Demandes que le serveur refuserait (plus de 100 caractères, ponctuation seule) | non envoyées (`SEARCH_SUGGESTIONS_MAX_LENGTH`, une lettre ou un chiffre) | « ni une saisie de plus de 100 caractères… » | rouge sur le code d'avant |
| **S15** Après Échap, la frappe ne rouvrait pas la liste | `onQueryChange` rouvre la liste | « après Échap, taper rouvre la liste » | rouge sur le code d'avant |

- api-mail inchangé par cette reprise (validation de la passe 2 : domain 221, infrastructure 749, application 4 283,
  api 1 380, integration 1 307 + 1 rouge `GreenMailBenchSmokeTests` vert isolé, banc GreenMail, sans lien).
- weda2 : `nx test mss-lib` 1 643 ✅, `nx test weda2` 2 683 ✅, `nx build weda2` ✅, ESLint 0 erreur.
- **Prévention** : `conventions/angular.md` § `suggestions-de-saisie-choisies-visibles` complétée (champs du
  formulaire, texte restauré).

### Reprise 3 (demandée par l'humain, 2026-11-12) — B4, B5, S16, S17 ; arbitrages S4/S5, S7

**Une seule règle pour la liste de suggestions** (recommandation de la 3ᵉ revue) : `MailSearchSuggestions` sait si la
liste est ouverte (`opened` / `closed`). Fermée, elle ne demande rien, ne montre rien, ne laisse rien désigner ni
choisir ; une demande en attente est annulée. Tous les chemins qui ferment la liste (Échap, clic ailleurs, lancer, choix
d'un patient, rejeu) passent par `closed()`, et l'ouverture demande les suggestions du texte visible.

| Constat | Correctif | Test | Preuve rouge |
|---|---|---|---|
| **B4** Demande de suggestions liste fermée (retour d'un mail, Échap, rejeu) : patients tracés jamais montrés | état ouvert / fermé dans `MailSearchSuggestions` ; `update` liste fermée n'envoie rien | `mail-search.suggestions.spec.ts` « liste fermée, remettre le texte… ne demande aucune suggestion » | rouge sur le code d'avant (2 demandes au lieu d'1) |
| **B5** Clic droit ou molette sur un patient suggéré l'ouvrait | `onChoose` : bouton principal seulement | « un clic droit ou molette… » | rouge sur le code d'avant |
| **S16** « Lancer la recherche » lançait `patient : …` | `launch()` refuse `patient :` / `type :` | « « patient : » puis « Lancer la recherche »… » | rouge sur le code d'avant |
| **S17** Recherches récentes remplacées sous la désignation | désignation remise à zéro au rechargement | « les recherches récentes rechargées… » | rouge sur le code d'avant |
| **S4/S5** (arbitrage : aligner) | « De », « À », « Objet » : nom et adresse, accents et casse ignorés (`search_normalize`), préfixe et formulaire | intégration `ATypedCriterion_SearchesLikeTheSuggestions_…` (`à : dupont`, `de : helene`, `objet : resultats`) | rouges sur le code d'avant |
| **S7** (arbitrage : couper au guillemet) | `SearchInput` : le préfixe s'arrête au premier guillemet fermé | intégration `APrefixStopsAtTheFirstQuote_…` ; unitaire `Parse_APrefixStopsAtTheFirstClosedQuote` | rouges sur le code d'avant |

- S6 (arbitrage) : le préfixe remplace le critère déjà posé — comportement actuel, inchangé. S11 : pas de bouton.
- weda2 : `nx test mss-lib` 1 647 ✅, `nx test weda2` 2 683 ✅, `nx build weda2` ✅, ESLint 0 erreur.
- **Prévention** : `conventions/angular.md` § `suggestions-de-saisie-choisies-visibles` réécrite autour de la règle
  unique (liste fermée = rien).

### Reprise 4 (demandée par l'humain, 2026-11-12) — B1, B2, S1 (arbitrage), S2, S3, S4

**Un critère tapé se lit comme les suggestions** (`TypedCriterion`, api-mail) : ses mots sont les suites de lettres et
de chiffres ; sans guillemets, chacun doit commencer un mot du champ, dans n'importe quel ordre ; entre guillemets, les
mots se suivent dans l'ordre strict (arbitrage S1). Mot et champ passent par la **même** fonction SQL
(`search_normalize`), jamais par son jumeau C#. Le critère d'un préfixe garde ses guillemets (`SearchInput`).

| Constat | Correctif | Test | Preuve rouge |
|---|---|---|---|
| **B1** « Objet » avec `’` ne trouvait plus rien | mots découpés sur la ponctuation, normalisés par `search_normalize` des deux côtés | intégration `ATypedCriterion_EveryWordInAnyOrder_…` (`objet : d’echographie`, `objet : "compte rendu d’échographie"`) | rouges sur le code d'avant |
| **B2** Ctrl+clic / Cmd+clic, appui glissé hors de l'entrée | choix au `click`, clic principal sans modificateur ; `mousedown` ne fait que garder le focus | « un Ctrl+clic ou Cmd+clic… », « appuyer… puis relâcher ailleurs… » | mutations : modificateurs ignorés → rouge ; choix à l'appui → rouge |
| **S1** (arbitrage) mots dans n'importe quel ordre ; ordre strict entre guillemets | `TypedCriterion` + `WhereHoldsEveryPart` ; « À » : tous les mots chez le **même** destinataire | intégration (`de : martin helene`, `de : "helene martin"`, `de : "martin helene"` → rien, `de : jean pierre`, `à : jean dupont`) ; unitaires `TypedCriterionTests` | rouges sur le code d'avant ; mutation « ordre strict ignoré » → rouge ; mutation « mots chez des destinataires différents » → rouge |
| **S3** requête en vol annulée 250 ms après la fermeture | la pause de frappe vit dans le `switchMap` (`timer`) : `''` annule aussitôt | « Échap annule aussitôt la demande… » | mutation `debounceTime` avant le `switchMap` → rouge |
| **S4** `de : "" martin` | une paire de guillemets vide est ignorée | unitaires `Parse_AnEmptyPairOfQuotes_IsDropped` ; intégration `de : "" helene` | rouges sur le code d'avant |
| **S2** coût des critères normalisés | préfiltre par mot « texte normalisé contient le mot » (sans perte) avant le test en début de mot | mesure `Docs/audits/findings/plans/20261112-task-449/results.txt` (reprise 4) | — |

- **S2, mesure** (11 291 mails, page de 51) : `ILIKE` de develop p95 ≈ 9 ms ; mots en début de mot sans préfiltre p95
  ≈ 64-75 ms ; **retenu** avec préfiltre p95 25 ms pour un mot rare. Un mot présent sur presque toutes les lignes
  (l'adresse de la boîte) reste ≈ 60 ms. Préfiltre par `SearchText` (index trigramme, 0,2 ms) écarté : colonne bâtie
  en arrière-plan, absente d'une boîte neuve.
- **Conséquence assumée de S1/S4/S5** : `%`, `_`, `\` tapés dans un critère séparent les mots, comme dans le plein texte
  (task-439) ; ils ne sont jamais des jokers. Trois tests existants affirmaient l'égalité littérale (`50%` ne trouve
  pas « Taux 500 ») : réécrits sur la garantie qu'ils protègent (jamais un joker : `5%0` ne trouve pas « 5770 ») ;
  mutation « critère passé tel quel au LIKE » → les 4 cas rouges. Un `50` tapé trouve désormais « 500 » (début de mot,
  comme les suggestions).
- Validation : api-mail build ✅, tests 7 970 ✅ (dont 1 321 d'intégration, 16 ignorés) ; weda2 `nx test mss-lib`
  1 650 ✅, `nx test weda2` 2 683 ✅, `nx build weda2` ✅, ESLint 0 erreur (51 + 48 avertissements, inchangés).
  Commit api-mail `452556d2`. Un premier passage de la suite complète en `--no-build` a tourné sur le binaire de la
  dernière mutation (18 échecs) : recompilé, relancé, vert — récidive consignée en mémoire (script de mutation qui
  restaure sans recompiler).
- Passe qualité (§Q) : diff relu (aucun reste de l'ancien motif, une seule voie de normalisation) ; rien à simplifier.

### Reprise 5 (demandée par l'humain, 2026-11-12) — B1, B2, S5, S6

| Constat | Correctif | Test | Preuve rouge |
|---|---|---|---|
| **B1** deux expressions voisines fusionnaient (regex de paire vide de la reprise 4) | regex retirée ; une paire vide est écartée **après** l'appariement des guillemets (`SearchPhrases` : seuls des mots comptent avant une expression ; `TypedCriterion` ignore les guillemets) | unitaires `Parse_TwoNeighbouringExpressions_StayTwoExpressions` (3 cas) ; intégration `APrefixBeforeTwoNeighbouringExpressions_…` (`de : "paul martin" "compte rendu"`) | `SearchInput` de la reprise 4 → 2 unitaires + l'intégration rouges ; mutation « une paire vide compte avant une expression » → rouge |
| **B2** un correspondant choisi ramenait ses homonymes | un critère qui est **entièrement une adresse bien formée** se compare exactement, casse ignorée (« De » : `FromAddress` ; « À » : `MailRecipients.Address`), dans le formulaire comme après un préfixe | intégration `AChosenAddress_IsThatCorrespondentOnly_…` (formulaire De / À, `de :`, `à :`) ; unitaires `Read_AWholeWellFormedAddress_IsComparedExactly` | mutation « adresse lue en mots » → 4 intégrations + 2 unitaires rouges |
| **S5** critère de plus de 10 mots tronqué en silence | refusé en 400 `ProblemDetails` (`SemanticSearchService.EnsureNoCriterionTooLong`) | intégration `ATypedCriterionOfMoreThanTenWords_Is400ProblemJson_…` ; unitaire `Read_ManyWords_IsTooLong` | mutation « critère trop long accepté » → rouge |
| **S6** changement de comportement à annoncer | dans la PR : `%`, `_`, `\` séparent les mots ; `50` trouve « 500 » (début de mot) | — | — |

- Validation : api-mail build ✅, tests 7 988 ✅ (dont 1 327 d'intégration, 16 ignorés), après recompilation du code
  restauré (le script de mutation finit désormais par un `dotnet build`). weda2 inchangé depuis la reprise 4 (1 650 +
  2 683 ✅). Commit api-mail `da6f0500`.

### Reprise 6 (demandée par l'humain, 2026-11-12) — B1, S1, S2, S3

| Constat | Correctif | Test | Preuve rouge |
|---|---|---|---|
| **B1** une adresse choisie de plus de 10 « mots » était refusée en 400 | le plafond ne vaut que pour un critère lu en mots (`Address is null`) | unitaire `Read_ALongAddress_IsNeverTooLong` ; intégration `AChosenAddress_…("long")` (adresse de 11 mots) | rouges sur le code de la reprise 5 (un premier exemple à 10 mots passait : allongé à 11) |
| **S1** `de : ""` n'était plus un critère vide ; `de : "Paul Martin" ""` cherchait `""` par le sens | blancs et paires vides = rien de tapé (`SearchInput.OrEmpty`, `TypedCriterion.IsEmpty`) | unitaires `Parse_OnlyEmptyPairsOfQuotes_IsNothingTyped`, `Read_NothingTyped_IsEmpty` ; intégration `de : ""` → 400 | rouges sur le code de la reprise 5 |
| **S2** `p.martin@x.fr,` reconnu comme adresse exacte | mêmes caractères exclus que `isWellFormedMailAddress` de weda2 | unitaire `Read_AnAddressWithPunctuationAround_IsReadAsWords` (4 cas) | rouges sur le code de la reprise 5 |
| **S3** le plafond comptait doublons et élisions | mots distincts (sans ordre strict) ; une lettre seule (élision) ne compte pas | unitaire `Read_RepeatedWordsAndElisions_…` ; intégration `objet : compte rendu de l'IRM de la …` → 200 | rouges sur le code de la reprise 5 |

- Relu comme un correctif (« qu'est-ce que ça casse ailleurs ? ») : le plafond, l'adresse et le vide sont décidés pour
  les deux lectures (adresse exacte, mots), consigne de la passe 6 ; `OrEmpty` ne change rien à un critère qui porte un
  mot ; les mots distincts ne s'appliquent pas à l'ordre strict (une expression garde ses répétitions).
- Validation : api-mail build ✅, tests 8 003 ✅ (dont 1 331 d'intégration, 16 ignorés), vert marqué (`421e4589`).
  weda2 inchangé (vert marqué à la passe 6).
- **Première reprise sur la boucle courte** (forge locale, en relecture humaine) : suite → `/review --code`.

### Reprise 7 (demandée par l'humain, 2026-11-12) — B1, S1, S2, S3

**Une seule borne, posée où les conditions SQL sont construites** (`SemanticSearchRepository.WhereHoldsEveryPart`, la
lecture en mots) : l'adresse comparée en entier (« De », « À ») n'y passe jamais, l'objet et le nom y passent. Le
contrôle dispersé du service (`EnsureNoCriterionTooLong`) est retiré.

| Constat | Correctif | Test | Preuve rouge |
|---|---|---|---|
| **B1** conditions SQL non bornées (`"a a … a"` ~245 `LIKE` ; exemption « adresse » appliquée à l'objet) | conditions = mots **distincts** ; borne dure `MaxConditions` = 20 (lettres seules comprises) en plus des 10 mots de 2 lettres et plus ; refus dans `WhereHoldsEveryPart` | unitaires `Read_ARepeatedLetterBetweenQuotes_IsOneCondition`, `Read_ManyDistinctOneLetterWords_IsTooLong` ; intégration `ATypedCriterion_CountsDistinctConditions_…` (`"a…a"` → 200 ; `a … z` → 400 ; « adresse » de 11 mots dans l'objet → 400) | mutations « borne dure retirée », « mots non dédoublonnés », « exemption adresse dans le dépôt » → rouges |
| **S1** `""` seul dans un champ listait toute la boîte | `IsEmpty` = blancs seulement : une paire vide ne garde aucune ligne (la barre : 400) | unitaire `Read_NothingTyped_IsEmpty` ; intégration `FORM-EMPTY-PAIR` → aucun résultat | mutation « paire vide = rien de tapé » → rouges |
| **S2** dédoublonnage par le jumeau C# | `OrdinalIgnoreCase` sur le texte tapé | unitaire `Read_TheSameWordInAnotherCase_…` | mutation `Ordinal` → rouge |
| **S3** le test « l'IRM » ne lisait qu'un 200 | il lit le message trouvé, et un cas où un mot manque ne trouve rien | intégration (`… l'IRM … du jour` → [1] ; `… l'IRM du genou` → []) | mutation « préfiltre et début de mot limités à 5 mots » → rouge |

- Validation : api-mail build ✅, tests 8 011 ✅ (dont 1 336 d'intégration, 16 ignorés), vert marqué (`3f81df39`).

### Écarts et décisions consignés

- **Identité patient** : la consigne `identite-patient-exacte` interdit `LIKE 'x%'` pour **désigner** un patient ; la
  task demande une **suggestion** par début de mot (décision humaine). Exception écrite dans la consigne : une
  suggestion complète un début de mot, ne désigne personne, et le médecin choisit dans la liste.
- Les recherches récentes au focus viennent de `GET /search/history` (5 premières) ; la route de suggestions exige
  2 caractères.
- La suppression de l'historique (« Effacer ») disparaît avec le composant d'historique du formulaire.

### Passe qualité (§Q)

- Diff relu : projection patient factorisée (`ToFoundPatient`), aucun autre cleanup appliqué ; pas de re-validation
  supplémentaire.

### Prévention (règle d'or)

- `conventions/csharp.md` § `route-identite-patient-jamais-exemptee` (nouvelle) ; § `identite-patient-exacte` complétée
  (exception de la suggestion par début de mot).

## Sonar log

- Mode A (chaîné), branche `feat/task-449-recherche-suggestions-pendant-la-frappe`, serveur 9.9.8 (`sonar.login`).
- Analyse 1 (`f10e6d80`) : `ANALYSIS SUCCESSFUL`, 5 passes OpenCover vertes (integration 1 302, 16 ignorés). Quality
  Gate **OK**. **1 issue nouveau code** : CA1861 (tableau constant dans un `Arg.Is` de
  `SearchSuggestionServiceTests`) → champ `static readonly` (`946d6e65`), test vert. Correction de test seulement :
  non ré-analysée (best-effort, 1 itération). Récidive comptée : `conventions/csharp.md` § CA1861, occurrences 7.
- Phase 2 (legacy) : rien à traiter (0 smell hors nouveau code).
- **Reprise 1** — analyse 2 (`68a0f76c`) : `ANALYSIS SUCCESSFUL`, 5 passes OpenCover vertes (integration 1 308,
  16 ignorés), Quality Gate **OK**, **0 issue nouveau code**, couverture nouveau code 96,3 %, 0 smell.
- **Reprise 3** — analyse 3 (`129294c1`) : Quality Gate **OK**, **1 issue nouveau code** : S3776 sur
  `SemanticSearchRepository.ApplyFieldFilters` (complexité 17, un `||` nom ou adresse ajouté par l'arbitrage S4/S5).
  Nouveau code : la blacklist S3776 ne s'applique pas (`conventions/csharp.md` § S3776). Critères tapés extraits en
  `ApplyTypedTextFilters` (`5d3716ad`), SQL identique ; build vert, 759 tests de recherche verts (dont 333 d'intégration).
  Récidive comptée : § S3776, occurrences 8.
- **Reprise 3** — analyse 4 (`5d3716ad`, confirmation) : Quality Gate **OK**, **0 issue nouveau code**, couverture
  nouveau code 96,3 %, couverture 97,8 %, 0 smell, duplication 0,4 %.

- **Reprise 4** — analyse 5 (`452556d2`) : Quality Gate **OK**, **0 issue nouveau code**, couverture nouveau code
  96,3 %, couverture 97,7 %, 0 smell, duplication 0,4 %.
- **Reprise 5** — analyse 6 (`da6f0500`) : Quality Gate **OK**, **2 issues nouveau code** : CA1862 ×2
  (`ToLower() ==` dans une requête EF, adresse choisie). Corrigé par `EF.Functions.ILike` sur un motif échappé
  (`93bf2adf`) ; test ajouté (un `_` d'adresse n'est pas un joker), vu rouge par mutation. CA1862 est une règle Roslyn :
  rebuild complet sans aucun avertissement CA1862, analyse de confirmation non relancée (best-effort, ~15 min évitées).
  Récidive comptée : `conventions/csharp.md` § CA1862, occurrences 3. Couverture nouveau code 96,3 %.
- **Reprises 6-7, après l'approbation de la revue anticipée** — analyse 7 (`3f81df39`), **une seule** sur le code approuvé :
  Quality Gate **OK**, **0 issue nouveau code**, couverture nouveau code 96,3 %, couverture 97,7 %, 0 smell. Vert marqué
  (`Tools/green/green.py`, par /sonar : 5 passes de tests complètes vertes).
### KPIs qualité (baseline → final)

| KPI | Baseline | Final |
|---|---|---|
| Quality Gate | OK | **OK** |
| Bugs / Vulnerabilities / Hotspots | 0 / 0 / 0 | 0 / 0 / 0 |
| Code Smells | 0 | 0 |
| Coverage | 97,8 % | 97,7 % |
| Duplication | 0,4 % | 0,4 % |
| Reliability / Security / Maintainability | A / A / A | A / A / A |
| New code — issues | — | 0 (CA1861, S3776, CA1862 ×2 corrigées en cours de cycle) |
| New code — coverage | — | 96,3 % |

## Lint log

- client-angular (code-only, `feature/nova-mss-weda-integration`, aucun git) : `npx nx run-many -t lint
  --projects=mss-lib,mss-e2e` (contournement task-367).
- **0 erreur** ; avertissements 51 (`mss-lib`, 52 avant : celui du composant d'historique retiré) + 48 (`mss-e2e`,
  inchangé) : aucun introduit.
- Itérations : 0. Build et tests déjà verts sur l'arbre final (fin de `/develop`).
- **Reprise 1** : relancé sur l'arbre repris — **0 erreur**, 51 + 48 avertissements (inchangés). Itérations : 0.
- **Reprise 2** : relancé — **0 erreur**, 51 + 48 avertissements (inchangés). Itérations : 0.
- **Reprise 3** : relancé — **0 erreur**, 51 + 48 avertissements (inchangés). Itérations : 0.
- **Reprise 4** : relancé — **0 erreur**, 51 + 48 avertissements (inchangés). Itérations : 0.
- **Reprise 5** : weda2 inchangé depuis la reprise 4 — résultat identique (0 erreur). Itérations : 0.
- **Reprises 6-7** : weda2 inchangé depuis la reprise 4 — résultat identique (0 erreur). Itérations : 0.

## Lint mobile log

- skipped — `client-mobile` absent des `**Repos**`.

## E2E log

| Voie | Jouée / réutilisée | Résultat | Dépôts couverts |
|---|---|---|---|
| mobile | jouée (reprise 5) | 61 verts, 0 flaky, 0 rouge, parité verte | api-mail `93bf2adf`, client-mobile `develop` `f775f17` |
| angular | jouée (reprise 5) | 84 verts dont E2E-SEARCH-013 et 014, 0 flaky, 0 rouge, parité verte | api-mail `93bf2adf`, client-angular (arbre non commité), Client/Mobile/e2e |

Passage 1 : un premier jeu mobile en parité rouge sur `E2E-BIO-004` (`develop` local de `client-mobile` en retard d'un
commit, `git pull --ff-only` puis voie rejouée, verte) ; flaky E2E-COMPOSE-001 consigné au registre (9ᵉ occurrence).
Reprises 1, 3, 4 et 5 : les deux voies rejouées, vertes, sans flaky. Reprise 2 (weda2 seulement) : voie Angular rejouée,
verte ; voie mobile réutilisée (empreinte inchangée).
Démontage vérifié : ports libres, aucun conteneur e2e résiduel.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-PATIENT-004 | 1 | headless | La vue « Mails du patient » reste ouverte et ses pages viennent du serveur | ✅ | — |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | ✅ |
| E2E-BIO-001 | 2 | headless | Acquitter un compte rendu de biologie, à son nom | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ✅ |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-BIO-004 | 1 | headless | Un compte rendu acquitté puis déplacé depuis un autre client garde son acquittement | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SETTINGS-004 | 1 | headless | Paramètres indisponibles : rien n'est écrasé | ✅ | — |
| E2E-SEARCH-001 | 2 | headless | Composer ses critères puis lancer la recherche | ✅ | ✅ (v1) · divergence (task-450) |
| E2E-SEARCH-002 | 1 | headless | Un mot rare et accentué trouve le message qui le contient | ✅ | ✅ |
| E2E-SEARCH-003 | 1 | headless | Un numéro de dossier trouve son message, et un seul | ✅ | ✅ |
| E2E-SEARCH-004 | 1 | headless | Un nom de patient tapé sans accent ni majuscule trouve ses messages, puis les messages partiels | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-005 | 1 | headless | Un mot absent de la boîte affiche « Aucun résultat » | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-006 | 1 | headless | Plus de résultats qu'une page — « Voir plus » affiche la suite, jusqu'au dernier | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-007 | 1 | headless | Une recherche en échec affiche un message, et l'ancienne liste n'est plus affichée | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-009 | 1 | headless | Fermer la recherche rend le dossier à la même position ; retirer une étiquette relance sans elle | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-010 | 1 | headless | Reconnaître un résultat et ouvrir le dossier du patient | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-SEARCH-012 | 1 | headless | Traiter tous les résultats d'une recherche | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-SEARCH-013 | 1 | headless | Trouver un patient en tapant les premières lettres de son nom | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-SEARCH-014 | 1 | headless | Restreindre la recherche à un expéditeur en tapant « de : » | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-SEARCH-008 | 1 | headless | Restreindre la recherche à un patient et à ses biologies anormales | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 2 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ | ✅ |
| E2E-MAILBOX-003 | 2 | headless | Rattacher ses boîtes depuis « Mes boîtes » en un geste — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-006 | 1 | headless | Après le rattachement, l'identité d'expéditeur et la signature sont déjà là | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | ✅ |
| E2E-AUDIT-001 | 1 | headless | Le titulaire lit au journal le message supprimé par son délégataire, au nom du délégataire | ✅ | — |
| E2E-AUDIT-002 | 1 | headless | Le journal d'audit montre chaque action sur un mail | ✅ | — |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | ✅ |
| E2E-SHARED-002 | 1 | headless | Le délégataire écrit pour le compte du titulaire — le destinataire voit qui a écrit, sa réponse revient à la boîte | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ✅ | ✅ |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | ✅ |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | ✅ |
| E2E-ERROR-001 | 1 | headless | Une erreur affiche un code et une référence à transmettre au support | ✅ | ✅ |

**Divergences temporaires ouvertes** (11) :

- E2E-SEARCH-001 [mobile] — le mobile adopte le formulaire à un seul niveau avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-004 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-005 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-006 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-007 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-009 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-010 [mobile] — la lecture enrichie arrive sur le mobile avec la refonte mobile — résorbée par task-451
- E2E-SEARCH-012 [mobile] — la sélection de tous les résultats arrive sur le mobile avec la refonte mobile — résorbée par task-451
- E2E-SEARCH-013 [mobile] — les suggestions arrivent sur le mobile avec la refonte mobile — résorbée par task-451
- E2E-SEARCH-014 [mobile] — les préfixes arrivent sur le mobile avec la refonte mobile — résorbée par task-451
- E2E-SEARCH-008 [mobile] — les critères médicaux arrivent sur le mobile avec la refonte mobile — résorbée par task-451

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Code Review Summary

### Passage 1 (2026-11-12) — CHANGES REQUESTED

Revue indépendante. Validation : api-mail build 0 erreur, domain 221, infrastructure 749, application 4 274, api 1 380,
integration 1 301 (17 ignorés), 0 échec ; dtos-mss build vert. Build et tests verts, Sonar QG OK, `/e2e` vert, règle 1b tenue (17 mutations). Un bloquant, dans
la barre de weda2. Détail : `questions/task-449.md`.

#### À corriger par la reprise

- **B1** — après Échap (ou un clic ailleurs), Entrée choisit encore la suggestion désignée : la vue « Mails du patient »
  d'un patient que le médecin n'a pas choisi s'ouvre, et la consultation est tracée. Flèches et Entrée-sur-désignation
  seulement liste ouverte ; `closeDropdown()` remet la désignation à -1.
- **S2** — la réponse précédente reste affichée (et désignable) pendant la pause de frappe et la requête.
- **S3** — `distinctUntilChanged` après le debounce peut laisser la liste vide (`ab`, retour, `b` en < 250 ms).
- **S8** — saisie des suggestions non bornée (un `LIKE` par mot sur chaque ligne).
- **S9** — recherche exacte : une expression rare de mots fréquents peut faire vérifier 25 000 messages ; plafonner les
  candidats vérifiés, réponse tronquée au plafond.
- **S10** — `SearchHistoryOwner` retombe sur la clé partagée de la boîte quand la personne est inconnue.
- **S12** — saisie de ponctuation seule → les 5 dernières recherches ; Redis indisponible fait échouer toute la réponse.

#### Arbitrage humain

- **S11** — « Effacer » l'historique a disparu avec le composant d'historique du formulaire (`DELETE /search/history`
  sans appelant). Recommandation forge : un « Effacer » dans la catégorie « Recherches récentes ».
- **S4 / S5** — critères tapés (`à :` sur l'adresse seule, accents comptés) ≠ suggestions (nom et adresse, accents
  ignorés). Recommandation forge : aligner les critères sur `search_normalize` (nom et adresse).
- **S6 / S7** — un préfixe remplace un critère déjà posé ; `de : martin "compte rendu"` prend toute la fin.
  Recommandation forge : couper le critère au premier guillemet fermé, et combiner avec un critère déjà posé.

### Passage 2 (2026-11-12, après la reprise 1) — CHANGES REQUESTED

Revue indépendante. B1 (barre), S2 (frappe), S3, S8, S9, S10, S12 : corrigés et prouvés. Deux bloquants **nouveaux**,
sur d'autres chemins que B1 (même famille : une suggestion choisie que le médecin ne voit pas) : reprise 2 automatique
(1 < 2, aucun bloquant revenu).

#### À corriger par la reprise

- **B2** — les champs « À ou Cc », « Objet » et « Nom de pièce jointe » appellent aussi `onKeyDown` liste ouverte :
  ↓ dans la barre (patient désigné), clic sur « Objet », Entrée → le patient s'ouvre au lieu de la recherche ; les
  flèches de ces champs déplacent la désignation de la barre. Gestionnaire propre aux champs (Entrée = lancer), ou
  désignation effacée quand la barre perd le focus.
- **B3** — `restoreCriteria` (Échap, « Fermer la recherche », `followShownSearch`) et le rejeu d'une recherche récente
  changent le texte sans prévenir les suggestions : à la réouverture, les suggestions de l'ancien texte s'affichent
  sous une barre vide, et ↓ + Entrée en ouvre une. `restoreCriteria` met les suggestions au texte restauré.
- **S13** — recherche exacte : quand le plafond de vérification est atteint, « Voir plus » rend des pages vides
  toujours marquées tronquées, et chaque clic relit 1 000 textes. Ne plus proposer la suite au-delà du plafond.
- **S14** — le client envoie des demandes refusées (plus de 100 caractères, aucune lettre ni chiffre) : ne pas les
  envoyer.
- **S15** — après Échap, la frappe ne rouvre pas la liste (le focus est resté dans la barre) : `onQueryChange` rouvre.

#### Arbitrage humain

- S11 **tranché par l'humain le 2026-11-12 : pas de bouton « Effacer »** (la catégorie « Recherches récentes »
  remplace l'historique du formulaire sans effacement).
- S4 / S5 **tranchés par l'humain le 2026-11-12 : aligner.** Les critères « De », « À » et « Objet » (tapés avec un
  préfixe ou saisis dans le formulaire) cherchent comme les suggestions : nom **et** adresse pour « De » et « À »,
  accents et casse ignorés (`search_normalize`). → à faire dans la prochaine reprise, test d'intégration vu rouge
  (`à : dupont` trouve le message dont seul le nom du destinataire porte « Dupont » ; `de : helene` trouve « Hélène »).
- S7 **tranché par l'humain le 2026-11-12 : couper au guillemet.** `de : martin "compte rendu"` → « De » contient
  « martin », et `"compte rendu"` est cherché en recherche exacte. → prochaine reprise, test unitaire et d'intégration.
- S6 **tranché par l'humain le 2026-11-12 : le préfixe remplace le critère déjà posé** (comportement actuel, aucun
  changement).

### Passage 3 (2026-11-12, après la reprise 2) — CHANGES REQUESTED, plafond atteint

Revue indépendante. B1, B2, B3, S2, S3, S13, S14, S15 corrigés (tests rouges sur le code d'avant). Deux bloquants
nouveaux, sur des consultations patient tracées : **B4** (le correctif de B3 envoie une demande de suggestions liste
fermée, et le serveur trace des patients jamais montrés), **B5** (clic droit ou molette sur un patient suggéré ouvre son
dossier) ; suggestions **S16** (`launch()` ignore `patient :` / `type :`), **S17** (recherches récentes remplacées sous
la désignation). Deux reprises déjà faites : **arrêt**, `questions/task-449.md` écrit.

### Passage 4 (2026-11-12, après la reprise 3) — CHANGES REQUESTED, plafond dépassé

Validation : build vert (api-mail, dtos-mss, weda2) ; tests api-mail 7 948 ✅ (dont 1 312 d'intégration, 16 ignorés),
`nx test mss-lib` 1 647 ✅, `nx test weda2` 2 683 ✅ ; Sonar QG OK, 0 issue nouveau code ; `/e2e` vert (mobile 61,
angular 84, parité verte). B3, B4, S16, S17 tiennent (tous les chemins de fermeture passent par `closed()`) ; S4/S5 et
S7 livrés et prouvés rouges. Revue indépendante : deux bloquants nouveaux, vérifiés par la forge.

#### À corriger par la reprise

- **B1** — `SemanticSearchRepository.NormalizedContainsPattern` normalise le motif par le jumeau C#
  (`SearchTerms.Normalize`) et la colonne par `search_normalize` (SQL). `unaccent` réécrit la ponctuation typographique,
  le jumeau non : vérifié en base, `unaccent('Compte rendu d’échographie')` = `Compte rendu d'echographie`, et le motif
  `d’echographie` ne le trouve plus. Régression de l'arbitrage S4/S5 sur le champ « Objet » / « De » / « À » (l'ancien
  `ILIKE` trouvait). Correctif : normaliser le motif par la même fonction SQL ; test d'intégration avec `’` vu rouge.
- **B2** — `MailSearchSuggestionsComponent.onChoose` choisit au `mousedown` et ne filtre que `button !== 0` : un
  Ctrl+clic ou Cmd+clic sur macOS (menu contextuel, `button === 0`) ouvre le dossier du patient, consultation tracée ;
  appuyer puis glisser hors de l'entrée choisit quand même. Correctif : choisir au `click`, refuser les touches de
  modification, garder `preventDefault()` au `mousedown` ; tests Ctrl+clic et glisser-hors vus rouges.
- S3 — `closed()` n'annule la requête en vol qu'après le délai de 250 ms (le `''` traverse le `debounceTime`) :
  annulation immédiate à la fermeture.
- S4 — `de : "" martin` : la paire de guillemets vide ne coupe pas le préfixe, le critère devient `"" martin` (0
  résultat).
- S2 — mesurer « De » / « Objet » normalisés sur la boîte de 11 178 messages ; préfiltre par `SearchText` (index
  trigramme) si le p95 dépasse celui de l'ancien `ILIKE`.

#### Arbitrage humain

- **S1** — les critères tapés cherchent une **sous-chaîne contiguë** ; les suggestions cherchent **chaque mot en début
  de mot, dans n'importe quel ordre**. `de : martin helene` propose « Hélène Martin », mais Entrée sans choisir rend 0
  résultat (idem `jean pierre` face à « Jean-Pierre »). L'arbitrage S4/S5 portait sur accents et casse. Recommandation
  forge : aligner aussi l'ordre des mots et la ponctuation (chaque mot tapé doit figurer, en début de mot), puisque la
  barre promet « comme les suggestions ».
  **Tranché par l'humain le 2026-11-12** : un critère tapé sans guillemets cherche **chaque mot, dans n'importe quel ordre**, comme les suggestions (`de : martin helene` trouve « Hélène Martin ») ; entre guillemets (`de : "Hélène Martin"`), les mots se cherchent **dans l'ordre strict**, d'un seul tenant. Lecture forge, inchangée par cet arbitrage : accents et casse restent ignorés dans les deux cas (S4/S5).

Prévention : `conventions/csharp.md` § recherche (motif normalisé par la même fonction SQL que la colonne) ;
`conventions/angular.md` § `suggestions-de-saisie-choisies-visibles` (clic principal sans modificateur, au `click`).
Trois reprises faites (plafond 2, la 3ᵉ demandée par l'humain) : **arrêt**, `questions/task-449.md` écrit.

### Passage 5 (2026-11-12, après la reprise 4) — CHANGES REQUESTED

Validation : build vert (api-mail, dtos-mss, weda2) ; tests api-mail 7 970 ✅ (dont 1 321 d'intégration, 16 ignorés),
`nx test mss-lib` 1 650 ✅, `nx test weda2` 2 683 ✅ ; Sonar QG OK, 0 issue nouveau code ; `/e2e` vert (mobile 61,
angular 84, parité verte). B1, B2 (passe 4), S1, S2, S3, S4 tiennent pour leur cas (preuves rouges consignées).
Vérifiés sans défaut : concordance du découpage C# / PostgreSQL sur les cas réalistes (`’`, œ, ß, ½, adresses) ;
préfiltre sans perte ; partie tapée envoyée en paramètre SQL ; « À » chez le même destinataire ; clic et annulation côté
weda2. Revue indépendante : deux bloquants nouveaux, **vérifiés par la forge**.

#### À corriger par la reprise

- **B1** — `SearchInput.EmptyQuotesPattern` (`"\s*"`) prend le guillemet fermant d'une expression, l'espace et l'ouvrant
  de la suivante : `de : "Paul Martin" "compte rendu"` devient `de : "Paul Martin compte rendu"` (4 mots dans l'ordre
  strict : 0 résultat, la recherche exacte de « compte rendu » disparaît) ; `de : martin "compte rendu" "IRM"` fusionne
  les deux expressions. Vérifié. Introduit par le correctif S4. Correctif : écarter les expressions **vides** après
  l'appariement des guillemets (`SearchPhrases`), pas par une regex préalable ; tests à deux expressions voisines, vus
  rouges.
- **B2** — un correspondant **choisi** est lu comme un critère **tapé** : `chooseCorrespondent` (destinataire),
  `selectFromContact` et Entrée sur une adresse bien formée (« De ») écrivent l'adresse dans `recipientAddress` /
  `fromAddress`, désormais lus mot à mot. Choisir « paul.martin@cardio.example » ramène aussi
  « jean-paul.martin@cardio.example ». Vérifié dans le code. Régression introduite par S1 (qui vise le texte tapé).
  Correctif recommandé, sans changer le contrat : un critère qui est **entièrement une adresse bien formée** se compare
  exactement (casse ignorée) ; tests vus rouges.
- S5 — au-delà de 10 mots, le critère est tronqué sans le dire (élargissement silencieux). Recommandation : refuser en 400
  `ProblemDetails` (« Critère trop long »), comme la saisie de plus de 100 caractères des suggestions.
- S6 — dire dans la PR le changement assumé : `%`, `_`, `\` séparent les mots, et `50` trouve « 500 » (début de mot).

#### Arbitrage humain

Aucun nouveau. (B2 a une variante qui toucherait le contrat — une liste exacte de destinataires choisis
`RecipientAddresses`, comme `FromAddresses` — non recommandée.)

Prévention : `conventions/csharp.md` § recherche (critère choisi comparé exactement ; regex de paire vide).
Quatre reprises faites (plafond 2) : **arrêt**, `questions/task-449.md` écrit.

### Passage 6 (2026-11-12, après la reprise 5) — CHANGES REQUESTED

Validation : build vert (api-mail, dtos-mss, weda2) ; tests api-mail 7 989 ✅ (dont 1 328 d'intégration, 16 ignorés),
`nx test mss-lib` 1 650 ✅, `nx test weda2` 2 683 ✅ ; vert marqué (`Tools/green/green.py`) pour api-mail `93bf2adf` et
weda2.
Revue indépendante du seul diff de la reprise 5 (`452556d2..93bf2adf`), lu d'abord pour ce qu'il a cassé. B1, B2, S5
de la passe 5 et CA1862 tiennent : `SearchPhrases` ne change que pour les paires vides ; `FromAddress` est stocké sans nom
affiché et `ILIKE` absorbe la casse ; seul `SemanticSearchService.SearchAsync` lit `FieldFilters` ; `ToContainsPattern`
rend la même chaîne qu'avant pour ses 4 appelants. Un bloquant nouveau, **né du correctif S5** (vérifié dans le code).

#### À corriger par la reprise

- **B1** — `TypedCriterion.IsTooLong` compte les mots d'une adresse même quand elle est comparée en entier (`Address`
  renseignée) : choisir `secretariat.cardiologie.pediatrique@ch-saint-jean-de-luz.mssante.fr` (plus de 10 « mots »)
  répond 400 « au plus 10 mots ». Le seul domaine `medecin.formation.mssante.fr` en compte déjà 4. Correctif :
  `IsTooLong = Address is null && …` ; test d'intégration avec une adresse de plus de 10 mots, vu rouge.
- S1 — une paire vide seule (`de : ""`) n'est plus un critère vide (200 vide au lieu du 400 « Tapez le texte du
  critère ») ; `de : "Paul Martin" ""` lance une recherche par le sens sur `""`. Correctif : un critère ou un reste fait
  de blancs et de paires vides est vide.
- S2 — la reconnaissance d'adresse du serveur accepte `<`, `>`, `,`, `;`, `(` que celle de weda2 exclut :
  `de : p.martin@x.fr,` devient une adresse exacte introuvable. Reprendre la classe de caractères du front.
- S3 — le plafond compte doublons et élisions (`l'IRM` = 2) : compter les mots **distincts**, ou dire ce qui est compté.

Prévention : `conventions/csharp.md` § recherche — un correctif qui ajoute une règle à un critère (plafond, exactitude)
vérifie ses **deux** lectures (adresse exacte / mots), c'est la 4ᵉ fois qu'un correctif de cette task casse le cas voisin.
Cinq reprises faites (plafond 2) : **arrêt**, `questions/task-449.md` écrit.

### Passage 7 (2026-11-12, revue anticipée après la reprise 6) — CHANGES REQUESTED

Première passe sur la boucle courte (`/review --code`, sans build ni Sonar ni e2e : ~3 min au lieu de ~45). B1, S1, S2,
S3 de la passe 6 corrigés là où ils visaient ; `OrEmpty` ne change aucun texte non vide ; la regex d'adresse reprend
celle de weda2. Un bloquant nouveau, **vérifié par la forge dans le code**, encore né du correctif précédent.

#### À corriger par la reprise

- **B1** — plus rien ne borne le nombre de conditions SQL d'un critère : en ordre strict les mots ne sont pas
  dédoublonnés et les mots d'une lettre ne comptent pas au plafond (`objet : "a a a … a"` → ~245 `LIKE` identiques par
  ligne, `unaccent` compris) ; et l'exemption « adresse » du plafond vaut aussi pour « Objet » et « De (nom) », qui ne
  comparent pas l'adresse en entier. Correctif : une **borne dure unique** sur les conditions effectivement émises
  (mots distincts, casse ignorée, préfiltre compris), appliquée là où elles sont construites ; l'exemption « adresse »
  seulement pour les champs qui comparent l'adresse en entier (`FromAddress`, `RecipientAddress`). Test rouge sur
  `"a a a … a"` et sur une « adresse » longue dans Objet.
- S1 — `""` seul dans un champ du formulaire passe la validation « au moins un critère » et liste toute la boîte, alors
  que `objet : ""` dans la barre répond 400 : un champ fait de paires vides doit compter comme vide aussi pour la
  validation (ou le dépôt garder « aucune ligne » comme avant).
- S2 — dédoublonner en ordinal insensible à la casse sur le texte tapé, pas par le jumeau C# `SearchTerms.Normalize`.
- S3 — l'intégration « l'IRM … » ne vérifie qu'un 200 sur une boîte vide : lire le message trouvé (règle 1b).

Prévention : `conventions/csharp.md` § recherche — une borne de coût SQL se pose **une fois**, sur ce qui est émis.
Six reprises faites (plafond 2) : **arrêt**, `questions/task-449.md` écrit.

### Passage 8 (2026-11-12, revue anticipée après la reprise 7) — APPROVED

Revue indépendante du diff de la reprise 7, lu d'abord pour ce qu'il casse : le 400 « trop long » est levé à la
construction de la requête (étape 1 de `SearchInternalAsync`), avant toute voie parallèle ou dégradée ; `IsUnexpectedFailure`
le laisse passer ; l'historique n'enregistre pas une recherche refusée ; `ApplyFieldFilters` n'a pas d'autre appelant.
Les preuves rouges de B1, S1, S2, S3 sont lues dans le Develop log.

**approved at** : api-mail `3f81df39` · dtos-mss `bb45953a` · client-angular `ce7741dd` + arbre de travail (inchangé depuis la reprise 4,
vert marqué).

#### Suggestions (dans la PR, non bloquantes)

- S1 — le refus dit « au plus 10 mots » aussi pour 21 lettres isolées, ou pour une adresse collée dans « Objet » :
  préciser le message (« une adresse se cherche dans De ou À »).
- S2 — aucun test ne verrait revenir `foreach (… criterion.Words)` dans le préfiltre (le coût reste borné par les 500
  caractères de la requête) ; les tests de refus ne lisent pas le `detail`.

## Timings

*(généré par `tools/timing/report.sh --task task-449 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 20 s | — | — | — | — |
| /develop | ok | 12 min 57 s | 20 (2 min 54 s) | 18 (58 min 47 s) | — | dtos-mss 1B/0T, api-mail 15B/14T, client-angular 4B/4T, reprise 7 |
| /sonar | ok | 10 min 22 s | 10 (3 min 49 s) | 37 (1 h 55 min) | 14 (5 min 33 s) | 1 itération(s), api-mail 10B/37T |
| /lint-angular | skipped | 0.8 s | — | — | — | weda2 inchangé depuis la reprise 4 |
| /lint-mobile | skipped | 0.8 s | — | — | — | client-mobile non touché |
| /e2e | ok | 20 min 12 s | — | — | — | e2e ×27 (3 h 02 min) |
| /review | failed | 8 min 06 s | 11 (1 min 20 s) | 7 (1 h 34 min) | — | api-mail 5B/5T, dtos-mss 5B/0T, client-angular 1B/2T, passage 6 : CHANGES REQUESTED (B1, né de S5), plafond de reprises dépassé |
| /review-code | ok | 4 min 04 s | — | — | — | — |
| **Total cycle** | | **56 min 06 s** | **41 (8 min 04 s)** | **62 (4 h 28 min)** | **14 (5 min 33 s)** | |

Autres commandes mesurées : lint ×5 (59 s), nuget-wait ×1 (24 s), restore ×1 (3.7 s)
