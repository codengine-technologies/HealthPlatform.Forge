# todo-task-227.md — Le contenu clinique d'un message ne doit pas pouvoir disparaître en silence

**Repos**: api-mail
**Epic**: E009
**Single frontend**: true
**Dependencies**: aucune. **task-225** (le décompte des sollicitations) et
**task-224** (les instruments du banc) sont mergées ; cette US ne dépend
d'aucune des deux, elle ferme la porte par laquelle une autre est passée.
**Priorité**: **1** — le défaut que cette US prévient s'est **déjà produit**, il
a franchi tout le cycle autonome avec 3 399 tests verts, et il n'a été arrêté
que par une relecture humaine. C'est le seul de tout le backlog dont le mode
d'échec est **la disparition silencieuse de contenu clinique**.

## Objective

Qu'un compte rendu reçu par le médecin ne puisse **jamais** cesser d'être analysé
sans que quelque chose ne le dise. Aujourd'hui la chaîne qui décode les documents
médicaux d'un message est gouvernée par un invariant **porteur mais muet** : rien
ne vérifie qu'il tient, donc un changement anodin ailleurs peut arrêter le
décodage sans qu'aucun test ne bronche et sans qu'aucune erreur ne s'affiche.

## Le constat — établi en lisant les tests, pas en les supposant absents

**L'invariant.** La présence d'une ligne `MailContents` signifie « ce message a
été analysé ». Quatre endroits en dépendent, et le deuxième décide si le CDA est
décodé ou non :

| Site | Ce qu'il en déduit |
|---|---|
| `MailRepository.GetEnrichedUidsAsync` | `MailContents.Any()` ⇒ ce UID est enrichi |
| `ImapService.ComputePendingEnrichmentAsync` (~:827) | l'exclut de `pendingUids` ⇒ **le CDA n'est pas décodé** |
| `BackgroundImapService` (~:142) | idem, côté synchronisation de fond |
| `MailRepository.TryResolveExistingMailAsync` | `ContentCount > 0` ⇒ « already enriched — skipping », **avant** la branche de promotion |

**Ce qui arrive quand l'invariant est cassé** : aucun `MailMedicalDocument`, aucun
rattachement patient, aucun résultat de biologie, aucun embedding pour la
recherche — et `NotifyAlreadyEnrichedAsync` annonce au poste du médecin que
l'analyse est **terminée**, donc il cesse d'attendre. Pas d'erreur, pas de log
d'alerte, pas de compteur qui bouge. Le médecin voit un message dont le compte
rendu n'arrivera jamais.

**Ce n'est pas une hypothèse.** task-222 a écrit exactement ce défaut (une
écriture de contenu depuis le chemin de lecture), il a traversé `/develop`,
`/forge-simplify`, `/sonar` et `/review` avec **3 399 tests verts**, et il a été
arrêté au seuil du merge par une relecture humaine. L'US a été annulée.

### Le pire n'est pas une absence de test, c'est un test qui ment

`BackgroundImapServiceTests.cs` :

```csharp
public async Task EnrichEmailsAsync_WithAlreadyEnrichedUids_SkipsThemAsync()
{
    _mockMailRepository.GetEnrichedUidsAsync(folder, uids)
        .Returns(new HashSet<uint>(uids));          // les 3 UIDs sont enrichis

    await _service.EnrichEmailsAsync(folder, uids, CancellationToken.None);

    await _mockMailRepository.Received(1).GetEnrichedUidsAsync(folder, uids);   // ← seule assertion
}
```

Ce test asserte que le marqueur a été **consulté**. Il n'asserte **pas** que rien
n'a été enrichi. **Il passerait à l'identique si le service ignorait totalement
le résultat.** Son voisin `EnrichEmailsAsync_WithEmptyUidList_DoesNothingAsync` a
le même défaut : `DoesNothing` n'est pas vérifié.

C'est la même famille de défaut que ceux que task-224 vient de corriger sur les
tableaux de bord — « un panneau d'erreurs vide se lit *aucune erreur* » devient
ici « un test nommé `SkipsThem` se lit *le skip est couvert* ». **Et c'est
vraisemblablement ce qui a rassuré tout le monde** : qui aurait cherché la
couverture de cet invariant aurait trouvé ce nom.

Le modèle du bon test existe **à trois lignes de là** :
`EnrichEmailsAsync_WhenNoSummaries_DoesNotTakeThePersistLockAsync` asserte un
vrai `DidNotReceive().AddNewMail(...)`.

### État réel de la couverture

| Maillon | État |
|---|---|
| Le marqueur est **consulté** | ✓ |
| **Le résultat du marqueur est respecté** (UID enrichi ⇒ non retraité) | ⛔ **non asserté** |
| `GetEnrichedUidsAsync`, cas **positif** (contenu ⇒ rapporté enrichi) | ⛔ **absent** — seul le cas négatif existe |
| Notification « déjà enrichi » émise vers le poste du médecin | ⛔ **absent** |
| Chaîne ouverture → analyse → contenu complet | ⛔ **absente** |
| Une lecture n'écrit pas dans le stock | ✓ (task-225) — mais garde *ce* défaut, pas sa classe |

## Ce qu'il ne faut PAS présumer

- **Ne pas se contenter de renommer les tests trompeurs.** Un nom exact devant
  une assertion faible reste une fausse couverture. C'est l'**assertion** qu'il
  faut écrire, sur le patron du voisin qui le fait déjà correctement.
- **Ne pas supprimer les deux tests fautifs.** Leurs scénarios sont les bons ;
  seule leur assertion manque. Les supprimer ferait *baisser* la couverture d'un
  invariant déjà nu.
- **Ne pas transformer le marqueur.** Il n'est pas demandé de remplacer
  « présence d'une ligne `MailContents` » par un champ explicite du genre
  `EnrichedAt`. Ce serait peut-être plus clair, mais c'est une migration de
  schéma sur une table portant des données de santé, et l'objet de cette US est
  de **rendre l'invariant vérifiable**, pas de le changer. À proposer séparément
  si le besoin s'en confirme.
- **Ne pas modifier le comportement produit.** Aucune ligne de production n'a
  besoin de changer pour satisfaire cette US, hors le garde-fou du point 5 si
  l'humain le retient. Si un test révèle un écart de comportement réel, **il faut
  s'arrêter et ouvrir une `questions/`** plutôt que d'ajuster le code pour faire
  passer le test : ce serait exactement la faute que cette US combat.
- **Ne pas se fier au nombre de tests verts comme preuve.** C'est le
  raisonnement qui a laissé passer task-222. La preuve attendue ici est
  **qu'un test échoue quand l'invariant est cassé** — constaté ROUGE, pas déduit.

## Contenu attendu

1. **Réparer les deux tests qui mentent** — `EnrichEmailsAsync_WithAlreadyEnrichedUids_SkipsThemAsync`
   et `EnrichEmailsAsync_WithEmptyUidList_DoesNothingAsync` doivent asserter ce
   que leur nom promet, sur le patron de leur voisin (`DidNotReceive`).
2. **Le cas positif du marqueur** — un message porteur d'une ligne de contenu est
   bien rapporté comme enrichi par `GetEnrichedUidsAsync`.
3. **Le verrouillage, réellement asserté** — sur plusieurs UIDs dont certains
   portent du contenu, seuls les autres sont traités, **et** le poste du médecin
   reçoit bien la notification « déjà enrichi » pour ceux qui ne le sont pas.
4. **La chaîne de bout en bout, sur base réelle** — message en-tête seul →
   ouverture par le chemin de lecture → **toujours en attente d'analyse** →
   analyse → contenu **et documents médicaux** présents → **plus en attente**.
   C'est le test qui aurait attrapé task-222.
5. **Le garde-fou de la classe de défaut** *(seul point de conception de cette
   US)* — l'ensemble des chemins autorisés à créer une ligne `MailContents` est
   **clos et asserté**, de sorte qu'un nouvel écrivain doive être ajouté
   **délibérément** à la liste plutôt que par accident. Forme laissée à
   l'implémentation (scan de sources, garde par réflexion, ou test d'architecture)
   ; l'exigence est qu'un écrivain non déclaré fasse **échouer** la suite.

   > **Arbitrage humain requis avant de traiter ce point.** Les points 1 à 4 sont
   > du test pur, sans risque. Le point 5 introduit une contrainte de conception
   > qui pèsera sur les futures évolutions, et il peut être retiré sans rien
   > déstabiliser du reste. Il est **le seul** qui protège la *classe* de défaut
   > plutôt qu'un défaut — c'est aussi pour cela qu'il mérite une décision
   > explicite et pas un choix par défaut.

## Hors scope

- **Tout changement du comportement produit** de la chaîne d'analyse. Cette US
  rend un invariant vérifiable ; elle ne le modifie pas.
- **Le remplacement du marqueur par un champ explicite** (`EnrichedAt` ou
  équivalent) — migration de schéma sur une table de données de santé, à
  arbitrer séparément.
- **Les autres lacunes de couverture** d'`api-mail`. Cette US traite **une**
  chaîne, celle dont le mode d'échec est la perte de contenu clinique.
- **Le harnais de mesure et les tableaux de bord** (task-224, mergée).
- **La couverture globale au sens Sonar** — l'objectif n'est pas un pourcentage,
  c'est un invariant gardé. Un point de couverture gagné ailleurs ne remplace pas
  ce test-là.

## Definition of Done

- [ ] Build passe (0 erreur, 0 avertissement)
- [ ] Tests passent (0 échec)
- [ ] `EnrichEmailsAsync_WithAlreadyEnrichedUids_SkipsThemAsync` asserte que
      **rien n'est enrichi** (pas seulement que le marqueur est consulté), et
      l'assertion est **constatée ROUGE** en neutralisant temporairement le
      filtrage — la preuve figure dans le `## Develop log`
- [ ] `EnrichEmailsAsync_WithEmptyUidList_DoesNothingAsync` asserte réellement
      qu'il ne se passe rien
- [ ] `GetEnrichedUidsAsync` : le cas **positif** est couvert (contenu présent ⇒
      UID rapporté enrichi)
- [ ] Le **verrouillage** est asserté : sur un lot mixte, seuls les UIDs sans
      contenu sont traités
- [ ] La **notification « déjà enrichi »** est asserté pour les UIDs déjà analysés
- [ ] **Test d'intégration sur base réelle** de la chaîne complète : ouverture
      d'un message en-tête seul ⇒ il reste en attente d'analyse ; après analyse ⇒
      contenu **et** documents médicaux présents, et plus en attente
- [ ] Chaque test neuf est **constaté ROUGE** avant que le comportement ne le
      rende vert — ou, pour les tests d'invariant, ROUGE en cassant
      temporairement l'invariant. Un test qui n'a jamais échoué ne prouve rien,
      et c'est la leçon centrale de cette US
- [ ] Aucune ligne de code de **production** modifiée (hors garde-fou du point 5
      si retenu) — vérifié par `git diff --stat`
- [ ] Aucune donnée de santé en clair dans les tests ni leurs jeux de données
      (INS, NIR, contenu CDA réel) — corpus synthétique uniquement
- [ ] *(si le point 5 est retenu)* un écrivain de `MailContents` non déclaré fait
      **échouer** la suite — constaté en ajoutant un écrivain factice

## Manual Test Plan

Aucun banc, aucun nœud distant : cette US se vérifie sur poste.

```bash
# 1. La suite complète doit être verte
cd Api/Mail
dotnet build HealthPlatform.Api.Mail.sln
dotnet test HealthPlatform.Api.Mail.sln

# 2. LA VÉRIFICATION QUI COMPTE — casser l'invariant et voir la suite le dire.
#    Dans ImapService.ComputePendingEnrichmentAsync, neutraliser le filtrage :
#        var pendingUids = uids.ToList();   // au lieu du Where(!alreadyEnriched)
dotnet test HealthPlatform.Api.Mail.sln   # DOIT échouer, en nommant l'invariant

# 3. Rétablir le filtrage, la suite redevient verte.
git checkout -- src/Application/Services/Implementation/ImapService.cs
dotnet test HealthPlatform.Api.Mail.sln
```

**Ce que l'humain doit voir** :

- à l'étape 2, **au moins un test échoue**, et son nom dit lequel des invariants
  est cassé — pas un échec obscur dans un test sans rapport ;
- à l'étape 3, retour au vert sans autre intervention ;
- dans le `git diff --stat` de la branche : **aucun fichier de production**
  modifié (hors garde-fou du point 5 s'il est retenu) ;
- *(si le point 5 est retenu)* en ajoutant un écrivain factice de `MailContents`
  dans le dépôt, la suite échoue en le nommant.

**Données de test** : corpus synthétique du dépôt, aucune donnée de santé réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — messagerie MSSanté du praticien.
- **Vague Ségur** : hors vague — l'US ne modifie aucun comportement fonctionnel ni
  contrat d'interopérabilité ; elle protège une exigence existante.
- **Exigences DSR honorées** : aucune nouvelle. **Protège** en revanche celles
  qui dépendent du décodage CDA — notamment les règles `SC.CDA/INT.*` et
  `SC.CDA/VISU.*` de E009 : sans analyse, les documents médicaux n'existent pas,
  donc ni leur visualisation ni leur intégration ne peuvent être conformes.
- **INS** : non manipulée directement. ⚠️ **Mais protégée indirectement, et c'est
  l'enjeu** : le rattachement patient dépend de l'INS portée par le CDA. Un
  message non analysé n'a **aucun** rattachement, donc l'identito-vigilance ne
  s'exerce sur rien. Les jeux de test utilisent des INS synthétiques.
- **Authentification PS** : inchangée (PSC / e-CPS, niveau eIDAS substantiel au
  moins) — l'US ne touche ni l'authentification ni le contrôle d'accès.
- **Habilitations** : inchangées. Aucun test ne franchit la frontière entre
  praticiens ; la base est par praticien.
- **Interop CI-SIS** : CDA r2 (volets CR de biologie / lettre de liaison). **En
  lecture seule et à travers des tests** : aucun document produit ni transformé.
  Le point est que le décodage **ait lieu**, pas qu'il change.
- **Tracé PGSSI-S** : aucun évènement métier nouveau. ⚠️ **Défaut de traçabilité
  constaté et à noter** : lorsque l'analyse est court-circuitée à tort, **rien
  n'est journalisé** — c'est ce silence qui a rendu task-222 invisible. Cette US
  ne le corrige pas (elle ne modifie pas la production) mais **le documente** ;
  si l'humain souhaite une trace d'exploitation sur ce chemin, c'est une US
  distincte à arbitrer.
- **Consentement patient** : non applicable — aucune donnée patient traitée, et
  la consultation reste celle du PS destinataire dans le cadre de la prise en
  charge.
- **Référentiels métier** : aucun nouveau. Les LOINC / NABM portés par les
  documents de test ne sont pas retouchés.
- **Hébergement HDS** : non pour l'exécution des tests (poste et conteneur de test
  local, données synthétiques). Oui en production pour la chaîne protégée.
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement, aucune nouvelle
  donnée collectée, aucune durée de conservation modifiée.

> **Pourquoi pas de fichier `.feature`** : le BDD (Reqnroll/SpecFlow) est
> déprécié dans cet atelier (CLAUDE.md règle 1, projet `mss.mail.bdd.tests`
> retiré avec task-008). Le comportement attendu est décrit ci-dessus et couvert
> par des tests unitaires et d'intégration.
