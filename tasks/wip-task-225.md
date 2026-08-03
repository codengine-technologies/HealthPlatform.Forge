# todo-task-225.md — Compter les allers-retours vers le serveur de messagerie

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune.
**Priorité**: **2** — c'est l'instrument qui manque à **task-224** pour prouver
son défaut 5, et à toute discussion future sur le coût d'un geste de lecture.

> ### Pourquoi cette US existe, et pourquoi elle est étroite
>
> Elle reprend **le seul acquis** de **task-222**, annulée le 2026-08-04 pour
> « trop de modifications non maîtrisées ». task-222 avait mêlé sur une même
> branche un correctif applicatif (retiré parce qu'il supprimait le décodage
> CDA), une passe de simplification, un refactoring du chemin d'ouverture et
> cette instrumentation. Le tout était devenu inévaluable.
>
> **Cette US ne livre qu'un instrument, et son périmètre est verrouillé par son
> « Hors scope ».** Le diff attendu est petit : deux fichiers neufs, trois
> fichiers touchés, aucune modification de comportement. Si le diff sort de ces
> bornes, c'est que la task a dérivé — s'arrêter et demander.

## Objective

Qu'on puisse dire, sur n'importe quelle demande, **combien de fois le serveur de
messagerie a réellement été sollicité** — au lieu de le déduire d'un temps, ce
qui ne l'a jamais prouvé.

## Le constat

Campagne de certification du 2026-08-03
(`reports/2026-08-03/report-journey-certif-n200-180029.md`), 200 médecins au
rythme réel. Sur la trace `4d911c462694fab4d7454de2453bb13f` (ouverture de
message à 439 ms), la télémétrie établissait :

- 19 ms pour résoudre le praticien et sa base ;
- **420 ms à l'intérieur du verrou de session IMAP**, avec `WaitTimeMs=0` — donc
  du travail, pas une file d'attente ;
- p95 serveur (497 ms) = p95 client (494 ms) : le temps est intégralement dans
  l'application.

**Et là elle s'arrêtait.** 420 ms est *compatible* avec quatre allers-retours de
95 ms, sans le prouver. Les commandes IMAP ne sont pas instrumentées à ce grain.

Cette ambiguïté a un coût déjà constaté : elle a permis à task-222 de bâtir une
cause plausible et fausse, puis un correctif qui aurait supprimé le décodage CDA
des messages ouverts avant analyse. Le défaut a été arrêté en relecture humaine.
Sans décompte, ni la cause ni sa réfutation n'étaient démontrables.

## Ce qu'il ne faut PAS présumer

- **Ne pas compter une session reprise du pool.** Réutiliser une connexion déjà
  ouverte ne parle pas au serveur. La compter gonflerait le décompte et lui
  ferait perdre sa seule propriété utile : être un **plancher exact** du nombre
  d'allers-retours.
- **Ne pas mettre d'identifiant dans les étiquettes.** Ni chemin de dossier, ni
  UID, ni nom de pièce jointe — en messagerie de santé, un nom de pièce jointe
  désigne couramment le patient et l'examen (leçon de task-213). Étiquettes
  littérales uniquement, ensemble fini connu à la compilation, sur le modèle de
  `MailProcessingMetrics.LockOperationFamily`.
- **Ne pas confondre le décompte avec un budget.** L'instrument dit combien
  d'allers-retours ont eu lieu, pas combien sont acceptables. La cible reste la
  grille SLO, validée par l'humain.
- **Ne pas conclure du décompte à un défaut produit.** Un message **pas encore
  analysé** *doit* solliciter le serveur : c'est le comportement voulu, celui qui
  permet au poste du médecin d'afficher les premiers éléments puis de recevoir la
  totalité après décodage du CDA. Un décompte non nul n'est une anomalie que si
  le message est déjà analysé.
- **⚠️ Ne JAMAIS écrire le contenu en base depuis le chemin de lecture** pour
  faire baisser le décompte. C'est l'erreur qui a coûté task-222 : la présence
  d'une ligne `MailContents` est le **marqueur d'analyse** du message
  (`GetEnrichedUidsAsync` → `MailContents.Any()`, consommé par
  `ComputePendingEnrichmentAsync` et `BackgroundImapService` ;
  `TryResolveExistingMailAsync` → `ContentCount > 0` ⇒ « already enriched —
  skipping » ; `GetCoverageCountsAsync` pour l'indicateur de couverture). La
  poser trop tôt écarte le message de l'analyse ⇒ CDA jamais décodé, aucun
  document médical, aucun rattachement patient, et `NotifyAlreadyEnrichedAsync`
  annonce au frontend que c'est terminé. **Perte de contenu clinique,
  silencieuse.**
- **Ne pas refactorer le chemin d'ouverture au-delà du strict nécessaire.**
  Poser les appels de comptage suffit. Toute décomposition de méthode qui ne
  serait pas indispensable au comptage est hors scope — c'est ainsi que le diff
  de task-222 est devenu inévaluable.

## Contenu attendu

1. **Un compteur par requête**, injectable, qui enregistre chaque commande
   envoyée au serveur de messagerie, exposé :
   - en métrique, par **commande** et par **famille d'opération** ;
   - en étiquette de trace, portant le total **propre à l'appel** (et non le
     cumul de la requête).
2. **Les appels de comptage sur le chemin d'ouverture d'un message** et sur
   l'ouverture de session — aux endroits où une commande part réellement.
3. **Les deux faces couvertes par des tests** : un message analysé se sert sans
   solliciter le serveur ; un message pas encore analysé le sollicite, et la
   séquence de commandes est celle attendue.
4. **La garde qui protège l'analyse** : un test prouvant que le chemin de lecture
   **n'écrit rien** en base. C'est le garde-fou qui interdit structurellement de
   refaire l'erreur de task-222.
5. **Deux avertissements en clair dans le code**, là où l'erreur se retenterait :
   dans `IMailRepository` et dans la documentation de `GetEmailContentAsync`.

## Hors scope

> Ce bloc est le **contrat de périmètre** de la task. Il est ce qui manquait à
> task-222.

- **Tout correctif de performance**, sur ce chemin ou un autre. Aucun défaut
  produit n'est établi sur l'ouverture d'un message ; cette US ne cherche pas à
  en corriger un, elle rend les futurs constats démontrables.
- **Toute modification du dépôt** (`IMailRepository`, `MailRepository`) autre que
  le commentaire d'avertissement du point 5. **Aucune méthode ajoutée.**
- **Toute modification du garde de lecture** `existingMail is { Content: not null }`.
- **Toute passe de simplification** ou de refactoring opportuniste sur les
  fichiers touchés.
- **Le harnais de mesure** (`tests/loadtest-k6/`) — confié à **task-224**
  (défaut 5).
- **Tout tir de campagne** : cette US livre un instrument, elle ne mesure rien au
  banc.

## Definition of Done

- [ ] Build passe (0 erreur, 0 avertissement)
- [ ] Tests passent (0 échec)
- [ ] Le décompte est exposé en métrique (par commande et par famille
      d'opération) et en étiquette de trace portant le total propre à l'appel
- [ ] Une session reprise du pool **n'incrémente pas** le décompte — vérifié par
      un test
- [ ] Test unitaire : message **analysé** ⇒ **0 sollicitation**, et le verrou de
      session **n'est pas acquis**
- [ ] Test unitaire : message **pas encore analysé** ⇒ la **séquence exacte** des
      commandes est assertée (pas seulement un total)
- [ ] Test d'intégration sur base réelle : message analysé ⇒ **0 sollicitation**
      (assertion sur le **nombre**, jamais sur un temps)
- [ ] **Garde anti-régression** : un test prouve qu'une lecture ne crée **aucune**
      ligne de contenu en base
- [ ] Aucune donnée de santé dans les étiquettes ni dans les logs ajoutés (ni
      chemin de dossier, ni UID, ni nom de pièce jointe) — vérifié par un test
- [ ] **Aucun changement de comportement observable de l'API** : le corps rendu
      au client est identique, message analysé comme non analysé
- [ ] **Périmètre respecté** : `git diff --stat` tient dans 2 fichiers neufs +
      4 fichiers touchés au maximum, et **aucune méthode n'est ajoutée au dépôt**.
      Le `## Develop log` recopie le `--stat` pour que ce soit vérifiable d'un
      coup d'œil.

## Manual Test Plan

Aucun banc distant n'est nécessaire : l'instrument s'observe sur une instance
locale.

```bash
# 1. Lancer l'API locale
cd Api/Mail
dotnet run --project src/AppHost

# 2. Relever le compteur avant / après chaque geste
curl -s http://127.0.0.1:5052/metrics | grep mssante_mail_server_solicitations_total
```

**Ce que l'humain doit voir** :

- en ouvrant **deux fois** un message **déjà analysé** : le compteur
  `{operation="GetEmailContent"}` **n'augmente pas**, et le message s'affiche
  normalement les deux fois ;
- en ouvrant un message **pas encore analysé** : le compteur augmente
  (`resolve_folder`, `open_folder`, `fetch_bodystructure`, `fetch_body_part`,
  `close_folder`), le message s'affiche immédiatement, **puis le contenu complet
  arrive après l'analyse** — documents médicaux et rattachement patient inclus.
  **C'est le point le plus important de ce plan de test** : c'est précisément ce
  flux que le correctif de task-222 cassait ;
- dans la trace de la requête (Seq / Jaeger) : l'étiquette
  `mss.mail_server.solicitations` porte le nombre de l'appel ;
- dans les étiquettes de la métrique : **aucun** nom de dossier, UID ni nom de
  pièce jointe ;
- `git diff --stat` sur la branche : un diff petit et lisible.

**Données de test** : boîte de test du praticien, aucune donnée de santé réelle
requise.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — messagerie MSSanté du praticien.
- **Vague Ségur** : hors vague — instrumentation interne, aucun contrat
  d'interopérabilité touché, aucun comportement fonctionnel modifié.
- **Exigences DSR honorées** : aucune nouvelle, aucune relâchée.
- **INS** : non manipulée.
- **Authentification PS** : inchangée (PSC / e-CPS, niveau eIDAS substantiel au
  moins).
- **Habilitations** : inchangées — l'instrument ne lit ni n'écrit aucune donnée
  métier.
- **Interop CI-SIS** : non applicable — aucun document produit ni transformé.
  ⚠️ **Point de vigilance explicite** : le décodage CDA des messages ouverts
  avant analyse ne doit subir **aucune** altération. C'est ce que le correctif de
  task-222 supprimait, et c'est ce que la garde du point 4 protège.
- **Tracé PGSSI-S** : aucun évènement métier touché. Les étiquettes de la
  nouvelle métrique et l'étiquette de trace ne portent **que** des littéraux
  écrits dans le code.
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui en production, mais l'US n'ajoute aucune donnée
  collectée ni conservée.
- **AIPD / impact RGPD** : néant — aucun nouveau traitement, aucune nouvelle
  donnée, aucune durée de conservation modifiée.

## Branches

- `api-mail` (pushed) : `feat/task-225-mail-server-solicitation-count` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-225-mail-server-solicitation-count
- `dtos-mss` (pushed, auto-inclus) : même nom de branche — aucun changement de contrat attendu, donc pas de PR si aucun commit.

> **Ordre décidé par l'humain le 2026-08-04** : task-225 **avant** task-224.
> Quatre critères de DOD de task-224 (défaut 5) s'appuient sur le compteur livré
> ici ; les enchaîner dans cet ordre évite de laisser ces critères non
> vérifiables. `/start 224` suivra.
