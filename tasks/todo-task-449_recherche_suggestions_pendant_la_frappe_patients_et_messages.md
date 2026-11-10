# todo-task-449.md — Recherche : suggestions pendant la frappe, patients et messages

**Repos**: api-mail, dtos-mss, client-angular
**Dependencies**: done-task-442 (formulaire), done-task-446 (patients trouvés, vue « Mails du patient » depuis les
résultats)
**Epic**: E023
**Priorité**: EPIC E023, demandée par l'humain le 2026-11-10. Une seule barre pour trouver un patient ou un message :
le médecin tape quelques lettres, choisit, et la recherche est faite.

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
- **Entrée** sans choisir de suggestion lance la recherche plein texte sur le texte tapé.
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
7. Ouvrir le journal de la boîte : la saisie `bern` y figure comme consultation, au nom de la personne, sans les lettres
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
