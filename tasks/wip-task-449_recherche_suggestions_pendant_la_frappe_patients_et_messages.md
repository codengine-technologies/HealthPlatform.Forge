# todo-task-449.md — Recherche : suggestions pendant la frappe, patients et messages

**Repos**: api-mail, dtos-mss, client-angular
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

## Timings

*(généré par `tools/timing/report.sh --task task-449 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 20 s | — | — | — | — |
| /develop | ok | 1 h 17 min | 3 (24 s) | 2 (7 min 18 s) | — | dtos-mss 1B/0T, api-mail 1B/1T, client-angular 1B/1T, suggestions, préfixes, guillemets ; dtos 600 |
| **Total cycle** | | **1 h 17 min** | **3 (24 s)** | **2 (7 min 18 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : nuget-wait ×1 (24 s), restore ×1 (3.7 s)
