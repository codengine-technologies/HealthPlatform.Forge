# task-222 — ANNULÉE

> ## 🚫 US ANNULÉE le 2026-08-04 — décision humaine
>
> **Motif** : trop de modifications non maîtrisées sur la branche. Elle mêlait un
> correctif applicatif retiré, une passe de simplification, un refactoring du
> chemin d'ouverture et l'instrumentation — un périmètre qu'on ne remet pas sous
> contrôle en le rapiéçant.
>
> **Ce qui a été défait** : PR `api-mail` #150 **fermée sans merge** ; branches
> `fix/task-222-open-enriched-mail-no-imap` **supprimées** sur `api-mail` et
> `dtos-mss` (locales et distantes). **Aucune ligne de cette US n'est sur
> `develop`.**
>
> **Ce qui est repris ailleurs** — rien de ce qui avait de la valeur n'est perdu :
>
> | Acquis | Repris par |
> |---|---|
> | Le décompte des sollicitations du serveur de messagerie | **task-225**, écrite strictement bornée à l'instrumentation |
> | L'artefact de mesure de l'étape 3 du parcours `journey` | **task-224**, défaut 5, priorité relevée 3 → 2 |
> | L'analyse du défaut évité (`MailContents` = marqueur d'enrichissement) | `questions/task-222.md` + garde-fous à reposer par task-225 |
>
> **Ce fichier est conservé comme dossier d'instruction**, pas comme travail
> livrable. Il vaut pour une seule chose : montrer comment une cause cohérente
> et fausse s'est bâtie sur un artefact de mesure, et jusqu'où elle est allée
> avant d'être arrêtée en relecture humaine. Tout ce qu'il affirme sur le
> correctif est faux — voir la section de correction en fin de fichier.

---


**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune pour ce qui est livré ici. ⚠️ **Ce qui reste à chiffrer
sur la relecture d'un message analysé dépend de task-224** (défaut 5 : la bande
de relecture du parcours n'est jamais analysée, donc l'étape 3 ne mesure pas ce
que son nom annonce).
**Priorité**: **2** — l'instrument manquant. Sans lui, on ne peut ni prouver
qu'un chemin sollicite le serveur, ni prouver qu'il ne le sollicite pas.

> ### ⚠️ US re-cadrée le 2026-08-04 — lire ceci avant tout
>
> **Cette US portait initialement un correctif de performance** : « Ouvrir un
> message déjà analysé ne doit plus repayer le trajet vers le serveur de
> messagerie », sur la base des 440 ms mesurés à l'étape 3 de la campagne du
> 2026-08-03.
>
> **Les deux prémisses se sont révélées fausses**, et le détail est conservé
> dans le `## Develop log` d'origine plus bas ainsi que dans
> `questions/task-222.md` :
>
> 1. **Le correctif proposé était dangereux.** Il faisait écrire le contenu en
>    base depuis le chemin de lecture. Or la présence d'une ligne de contenu est
>    le **marqueur d'analyse** du message : la poser trop tôt écarte le message
>    de l'analyse ⇒ CDA jamais décodé, aucun document médical, aucun rattachement
>    patient, et le poste du médecin reçoit l'annonce « analyse terminée ». Perte
>    de contenu clinique, silencieuse. Retiré (`5da54bc`), garde-fous posés.
> 2. **Le constat lui-même était un artefact de mesure.** Le parcours simulé
>    n'appelle jamais l'analyse, et sa bande « chaude » n'est donc jamais
>    analysée : l'étape 3 mesurait des messages **jamais analysés**. D'où
>    l'égalité 440 ≈ 442 ms avec l'étape « message froid » — les deux mesuraient
>    la même chose.
>
> **Décision humaine du 2026-08-04** : task-222 est re-cadrée sur **la mesure**
> (ci-dessous, livrée), et **la correction du harnais passe à task-224**
> (défaut 5). Il n'est **pas établi** qu'un défaut produit existe sur ce geste ;
> le rouvrir demandera une mesure faite avec un instrument corrigé.

## Objective

Qu'on puisse dire, sur n'importe quelle demande, **combien de fois le serveur de
messagerie a réellement été sollicité** — au lieu de le déduire d'un temps, ce
qui ne l'a jamais prouvé.

C'est un instrument, pas un correctif : il ne change aucun comportement. Il rend
décidables deux affirmations qui ne l'étaient pas — « ce chemin ne parle plus au
serveur » et, symétriquement, « cette étape de mesure ne mesure pas ce qu'elle
annonce ».

## Ce que la campagne pouvait dire, et ce qu'elle ne pouvait pas

Campagne de certification du 2026-08-03 (`report-journey-certif-n200-180029.md`),
200 médecins au rythme réel, 6 343 ouvertures de message.

**Ce qu'elle établissait** — sur la trace
`4d911c462694fab4d7454de2453bb13f` (ouverture à 439 ms) : 19 ms pour résoudre le
praticien et sa base, **420 ms à l'intérieur du verrou de session IMAP** avec
`WaitTimeMs=0` (donc du travail, pas une file d'attente), et un p95 serveur
(497 ms) égal au p95 client (494 ms) — le temps est intégralement dans
l'application.

**Ce qu'elle ne pouvait pas établir** — **le nombre d'allers-retours**. 420 ms
est *compatible* avec quatre allers-retours de 95 ms, sans le prouver, et les
commandes IMAP n'étaient pas instrumentées à ce grain. Cette ambiguïté est
exactement ce qui a permis de bâtir une cause plausible et fausse.

**Ce que l'instrument a immédiatement montré** — que l'étape 3, annoncée « servie
base », **sollicitait le serveur cinq fois**. Elle ne mesurait donc pas une
relecture. C'est le premier usage du décompte, et il a servi contre l'instrument
plutôt que contre le produit.

## Ce qu'il ne faut PAS présumer

- **Ne pas confondre le décompte avec un budget.** L'instrument ne dit pas
  combien d'allers-retours sont acceptables ; il dit combien il y en a eu. La
  cible reste la grille SLO, validée par l'humain.
- **Ne pas compter une session reprise du pool.** Réutiliser une connexion déjà
  ouverte ne parle pas au serveur. Compter cette reprise gonflerait le décompte
  et lui ferait perdre sa propriété utile : être un **plancher exact**.
- **Ne pas mettre d'identifiant dans les étiquettes.** Ni chemin de dossier, ni
  UID, ni nom de pièce jointe — en messagerie de santé un nom de pièce jointe
  désigne couramment le patient et l'examen (leçon de task-213). Étiquettes
  littérales, ensemble fini connu à la compilation.
- **Ne pas conclure du décompte à un défaut produit.** Un message pas encore
  analysé **doit** solliciter le serveur : c'est le comportement voulu, celui qui
  permet au poste du médecin d'afficher les premiers éléments puis de recevoir la
  totalité après décodage du CDA. Un décompte non nul n'est une anomalie que si
  le message est analysé.
- **Ne pas écrire le contenu depuis le chemin de lecture pour faire baisser le
  décompte.** C'est la voie qui a failli passer. Elle est désormais interdite par
  trois garde-fous dans le code.

## Contenu attendu

1. **Le décompte des sollicitations du serveur de messagerie, par requête** —
   exposé en métrique (par commande et par famille d'opération) et en étiquette
   de trace, et injectable pour être assertable en test.
2. **Les deux faces couvertes par des tests** : un message analysé se sert sans
   solliciter le serveur ; un message pas encore analysé le sollicite, et la
   séquence de commandes est celle attendue.
3. **La garde qui protège l'analyse** : un test prouvant que le chemin de lecture
   **n'écrit rien** en base — c'est ce qui empêche la réintroduction du défaut
   retiré.
4. **Le constat sur l'instrument, écrit et transmis** : l'étape 3 du parcours ne
   mesure pas ce qu'elle annonce, avec le levier de vérification, remis à
   task-224.

## Hors scope

- **La correction du harnais** — la chauffe de la bande de relecture doit passer
  par l'analyse elle-même. **Confié à task-224** (défaut 5), décision du
  2026-08-04.
- **Tout correctif applicatif sur le chemin d'ouverture** : aucun défaut produit
  n'est établi sur ce geste. À rouvrir seulement si une mesure faite avec un
  instrument corrigé en montre un.
- **Le tir de campagne** : cette US livre un instrument, elle ne mesure rien au
  banc. Le chiffrage de la relecture viendra après task-224.
- La suppression / le marquage comme lu, l'envoi (task-216), la grille SLO.

## Definition of Done

- [ ] Build passe (0 erreur)
- [ ] Tests passent (0 échec)
- [ ] Le **décompte des sollicitations du serveur de messagerie par requête** est
      instrumenté : métrique par commande et par famille d'opération, étiquette de
      trace portant le total propre à l'appel
- [ ] Une session reprise du pool **n'incrémente pas** le décompte (propriété de
      plancher exact) — vérifié par construction et documenté
- [ ] Tests unitaires des deux faces : message analysé ⇒ **0 sollicitation** et
      verrou de session non acquis ; message pas encore analysé ⇒ la **séquence
      exacte** des commandes est assertée
- [ ] Test d'intégration sur base réelle : message analysé ⇒ **0 sollicitation**
      (assertion sur le **nombre**, pas sur un temps)
- [ ] **Garde anti-régression** : un test prouve qu'une lecture ne crée **aucune**
      ligne de contenu en base, sous peine de supprimer le décodage CDA
- [ ] Aucune donnée de santé dans les étiquettes ni dans les logs ajoutés (ni
      chemin de dossier, ni UID, ni nom de pièce jointe)
- [ ] Aucun changement de comportement observable de l'API (le corps rendu au
      client est identique, message analysé comme non analysé)
- [ ] Le constat sur l'étape 3 du parcours est écrit et transmis à task-224

## Manual Test Plan

Aucun banc distant n'est nécessaire : l'instrument s'observe sur une instance
locale.

```bash
# 1. Lancer l'API locale
cd Api/Mail
dotnet run --project src/AppHost

# 2. Ouvrir un message DÉJÀ ANALYSÉ dans le client, deux fois de suite,
#    puis relever le compteur
curl -s http://127.0.0.1:5052/metrics | grep mssante_mail_server_solicitations_total

# 3. Ouvrir un message PAS ENCORE ANALYSÉ (message fraîchement reçu, avant
#    que l'analyse ne soit passée), puis relever à nouveau
curl -s http://127.0.0.1:5052/metrics | grep mssante_mail_server_solicitations_total
```

**Ce que l'humain doit voir** :

- sur un message **déjà analysé** : le compteur
  `mssante_mail_server_solicitations_total{operation="GetEmailContent"}`
  **n'augmente pas**, et le message s'affiche normalement ;
- sur un message **pas encore analysé** : le compteur augmente de 5
  (`resolve_folder`, `open_folder`, `fetch_bodystructure`, `fetch_body_part`,
  `close_folder`), le message s'affiche, **puis le contenu complet arrive après
  l'analyse** — documents médicaux et rattachement patient inclus. C'est
  précisément ce flux que le correctif retiré cassait : le vérifier est le point
  le plus important de ce plan de test ;
- dans la trace de la requête (Seq / Jaeger) : l'étiquette
  `mss.mail_server.solicitations` porte le nombre de l'appel ;
- dans les étiquettes de la métrique : **aucun** nom de dossier, UID ni nom de
  pièce jointe.

**Données de test** : boîte de test du praticien, aucune donnée de santé réelle
requise.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — messagerie MSSanté du praticien.
- **Vague Ségur** : hors vague — instrumentation interne, aucun contrat
  d'interopérabilité touché, aucun comportement fonctionnel modifié.
- **Exigences DSR honorées** : aucune nouvelle, aucune relâchée.
- **INS** : non manipulée.
- **Authentification PS** : inchangée (PSC / e-CPS).
- **Habilitations** : inchangées — l'instrument ne lit ni n'écrit aucune donnée
  métier.
- **Interop CI-SIS** : non applicable. ⚠️ **Point de vigilance honoré** : le
  correctif initialement proposé aurait supprimé le décodage CDA des messages
  ouverts avant analyse ; il a été retiré pour cette raison, et trois garde-fous
  interdisent sa réintroduction.
- **Tracé PGSSI-S** : aucun évènement métier touché. Les étiquettes de la
  nouvelle métrique et l'étiquette de trace ne portent **que** des littéraux
  écrits dans le code — aucun identifiant, aucune donnée de santé.
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui en production, mais l'US n'ajoute aucune donnée
  collectée ni conservée.
- **AIPD / impact RGPD** : néant — aucun nouveau traitement, aucune nouvelle
  donnée, aucune durée de conservation modifiée.

---

> ## Historique d'exécution — à lire avec la section de correction en fin de fichier
>
> Les sections qui suivent (`## Develop log`, `## Simplify log`, `## Sonar log`,
> `## PRs`, `## Code Review Summary`) datent de la **version initiale** de la US
> et décrivent le correctif qui a été **retiré**. Elles sont conservées
> **non corrigées** : c'est leur raisonnement qu'il faut pouvoir relire pour
> comprendre comment une cause cohérente s'est bâtie sur un artefact de mesure.
> La `## ⛔ Correction du 2026-08-04` en fin de fichier prévaut sur elles.

## Branches

- `api-mail` (pushed) : `fix/task-222-open-enriched-mail-no-imap` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-222-open-enriched-mail-no-imap
- `dtos-mss` (pushed, auto-inclus) : `fix/task-222-open-enriched-mail-no-imap` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-222-open-enriched-mail-no-imap (aucun changement de contrat attendu — pas de PR si aucun commit)

## Develop log

- **Repos touchés** : `api-mail` uniquement. `dtos-mss` : aucun changement de
  contrat (branche créée par `/start`, restée vide → pas de PR, pas de publish
  NuGet). `client-angular` / `client-mobile` / `client-blazor` : hors scope
  (`**Single frontend**: true` — la US corrige un chemin d'accès backend, la
  réponse de l'API est inchangée).
- **DTOs publiés** : aucun changement DTO.
- **Interop publié** : aucun changement interop.
- **Commits** (`fix/task-222-open-enriched-mail-no-imap`) :
  - `458fc48` feat(telemetry): compter les sollicitations du serveur de messagerie par requête
  - `317a403` fix(mail): ouvrir un message déjà analysé ne repaye plus le trajet vers le serveur
- **Build / tests locaux** : ✓ `dotnet build` 0 erreur / 0 avertissement ;
  `dotnet test` **3 399 réussis, 0 échec**, 16 ignorés (tests d'intégration
  exigeant un IMAP vivant, ignorés d'avance). Aucun des 3 rouges pré-existants
  connus ne s'est manifesté.

### La cause, close

Le décompte manquant est instrumenté (`IMailServerSolicitationRecorder`,
`Scoped` = une instance par requête ; compteur
`mssante_mail_server_solicitations_total{command,operation}` + étiquette de
trace `mss.mail_server.solicitations`). Une session reprise du pool ne compte
pas : le décompte est une **borne inférieure exacte** du nombre
d'allers-retours, pas une estimation.

**Sur cette base, la cause est close — et ce n'était pas quatre allers-retours
de trop, c'était l'absence d'une écriture.**

`GetEmailContentAsync` **lisait** le stock (`ImapService.cs:1982`) sans jamais
**l'écrire**. Le corps ramené du serveur était assaini, renvoyé, puis **jeté**.
Le message ne devenait donc jamais « stocké », et chaque ouverture repayait le
trajet en entier — d'où le verrou de session pris **inconditionnellement**
(ex-ligne 1991) que la télémétrie fine avait vu, et d'où les trois faits du
constat, tous les trois expliqués par cette seule asymétrie :

| Fait du constat | Ce que l'absence d'écriture en retour explique |
|---|---|
| 440 ms (chaud) ≈ 442 ms (froid) | il n'y avait **pas** de chaud : chaque ouverture était froide |
| PJ du même message en 34 ms | `GetAttachmentAsync` **écrit** en retour (`UpdateAttachmentAsync`) — le contre-exemple était le témoin du correctif |
| aucune dérive avec la charge | un trajet payé une fois par ouverture est un coût **fixe**, pas de la contention |

Le harnais `journey` chauffait bien sa bande de relecture (`warmUpOwnMailbox`,
`scenarios/journey.js`) en appelant `getEmailContent` sur chaque UID chaud —
mais son commentaire « le GET contenu matérialise le MailContent » était
**faux** : rien ne le matérialisait. L'étape 3 mesurait donc du froid en croyant
mesurer du chaud. Le harnais n'est pas en cause (il décrivait le comportement
attendu), il était le premier à en souffrir.

**Le PO avait raison sur le fond** : ce n'était pas l'absence d'un cache,
c'était le chemin d'accès. Aucun cache n'a été ajouté — l'écriture en retour
**complète le stock que la voie rapide lisait déjà**.

### Ce qui a été écrit

`SaveMailContentAsync` (dépôt), la symétrie exacte de `UpdateAttachmentAsync`.
Chaque clause du contrat est un garde-fou, aucune n'est une commodité :

- **génération courante** (task-179) : la même identité `(dossier, uid,
  génération)` que celle que lit `GetMailAsync` ;
- **n'invente jamais de ligne `Mail`** → **cloisonnement par praticien**
  (point de vigilance de la US) : un contenu ne peut pas être greffé sur une
  boîte qui ne porte pas le message. La base est déjà par praticien ; cette
  clause interdit en plus d'y écrire pour un message absent ;
- **idempotente** : n'écrase pas le contenu de la chaîne d'enrichissement, plus
  riche (résumé, embedding, documents médicaux) ;
- **refuse un corps vide des deux côtés** : sinon elle fabriquerait l'état
  « présent mais inexploitable » que la lecture rejette — donc une boucle.

L'écriture en retour est **best-effort** : le médecin a son contenu en main, un
incident de stockage ne doit pas le lui retirer (il coûte seulement une
sollicitation de plus à l'ouverture suivante).

**Effet de bord assumé, et c'est une correction** : une ligne de contenu
entièrement vide (promotion d'en-tête interrompue) n'est plus servie — elle
affichait un **écran blanc définitivement**, puisque rien ne repassait jamais
dessus. Le résumé et les documents médicaux comptent autant que le corps : un
message dont toute la valeur clinique est dans son CDA a souvent un corps vide,
et le re-solliciter le renverrait **sans** ses documents médicaux (la voie
serveur ne les porte pas). Le contenu clinique n'est jamais échangé contre un
corps vide.

### Contenu périmé côté serveur — tranché

**Il ne peut pas l'être.** Dans IMAP (RFC 3501) le corps d'un message d'UID
donné est **immuable** au sein d'une génération de dossier : seuls les marqueurs
changent, et un contenu différent est un autre message, donc un autre UID. Si le
serveur renumérote (`UIDVALIDITY`), l'identité stockée n'est plus celle du
dossier courant : le filtre de génération de task-179 cesse de servir la ligne
périmée et le contenu est re-sollicité. L'écriture en retour **n'ouvre donc
aucune fenêtre de péremption** — le médecin ne peut pas voir un document
clinique périmé. Couvert par
`SaveMailContentAsync_WhenMailBelongsToAPreviousGeneration_WritesNothingAsync`.

### Vérification demandée sur `mssante_lock_hold_duration_seconds`

Vérifié : **l'émission est correcte, le défaut n'est pas dans le code.**
`ImapLockScope.DisposeAsync` enregistre bien la détention avec la famille
d'opération depuis task-214 (`MailProcessingMetrics.RecordLockHold(...,
_tags.Family, _tags.Lane)`), et `report.py` interroge bien
`sum by (le, operation) (rate(mssante_lock_hold_duration_seconds_bucket
{lock="imap_session"}[1m]))`. Le silence sur la fenêtre du tir est donc côté
**observation** (scrape / fenêtre `[1m]` face à un débit de parcours très bas :
3 111 itérations sur 35 min), pas côté instrumentation. Ce n'est **pas** la même
famille de défaut que task-214. Hors scope de ce correctif — à confirmer au
prochain tir, l'instrument étant en place.

### DOD — auto-contrôle

| Critère | État |
|---|---|
| Build passe (0 erreur) | ✓ |
| Tests passent (0 échec) | ✓ 3 399 / 0 |
| Décompte des sollicitations instrumenté + cause close dans le Develop log | ✓ (ci-dessus) |
| Tests unitaires du chemin corrigé (contenu présent / absent / présent mais invalide) | ✓ 6 tests, `ImapServiceTests` |
| Test d'intégration : ouverture d'un message déjà analysé ne sollicite plus le serveur (assertion sur le **nombre**) | ✓ 3 tests sur **vrai PostgreSQL**, `MailContentServedFromStoreIntegrationTests` — dont la preuve de bout en bout : 1re ouverture sollicite + stocke, **2e sollicite zéro fois** |
| Comportement en cas de contenu périmé tranché, écrit, couvert par un test | ✓ (immuabilité IMAP + garde de génération) |
| Aucune donnée de santé en clair dans les logs ajoutés | ✓ étiquettes littérales uniquement ; aucun corps, INS, chemin de dossier ni nom de PJ |
| Cloisonnement par praticien préservé (point de vigilance) | ✓ `SaveMailContentAsync_WhenNoMailRow_WritesNothingAsync` |
| **Tir `journey` K=1, étape 3 ≤ 100 ms p50 / ≤ 500 ms p95** | ⛔ **non exécuté — déféré au test humain (HAG)** |
| **Aucune régression sur les 7 autres étapes vs `report-journey-certif-n200-180029.md`** | ⛔ **non exécuté — déféré au test humain (HAG)** |

**Pourquoi les deux derniers ne sont pas faits, précisément** — deux blocages
matériels, aucun d'eux contournable par la forge :

1. **Le banc exige un nœud distant.** Le Manual Test Plan lui-même impose
   `MSS_LOADTEST_MAIL_HOST=<ip-noeud>` (serveurs de messagerie **hors** de la
   machine de mesure) et un tir de **35 minutes au rythme réel**
   (`JOURNEY_TIME_COMPRESSION=1`, seule forme qui rend un verdict opposable). La
   forge n'a pas ce nœud.
2. **Le rapport de référence est absent de cette machine.**
   `tests/loadtest-k6/reports/` est git-ignoré (seul `INDEX.md` est suivi) et ne
   contient localement que `2026-07-25`, `2026-07-26`, `2026-07-27`. Le
   répertoire `2026-08-03/` n'existe pas ; `INDEX.md` porte bien la ligne du tir
   (`report-journey-certif-n200-180029.md`, 200 VU, PASS) mais le fichier
   lui-même n'est pas là. La comparaison étape par étape exigée par le DOD est
   donc impossible ici.

La chaîne de causalité est en revanche **prouvée par test** sans le banc : le
test d'intégration établit que la seconde ouverture d'un message dont le contenu
a été stocké sollicite le serveur **zéro fois**, ce qui est l'énoncé même du DOD
(« assertion sur le nombre de sollicitations, pas sur un temps »). Le banc reste
nécessaire pour **chiffrer** le gain et confirmer l'absence de régression sur les
7 autres étapes — c'est le geste humain du HAG.

### Note pour le prochain tir `journey`

Le commentaire de `warmUpOwnMailbox` (`tests/loadtest-k6/scenarios/journey.js`)
affirme que le GET contenu matérialise le `MailContent`. C'était faux avant ce
correctif ; **c'est vrai depuis**. La chauffe du harnais fonctionne donc
désormais comme elle le prétendait, sans qu'il faille y toucher. En revanche
l'avertissement sur le partage de seed avec un tir `enrich`/`mixed` devient plus
large : la bande **chaude** matérialise elle aussi du `MailContent` maintenant.
Signalé, non modifié — l'outillage de mesure est task-224.

- **Étape suivante** : `/forge-simplify task-222`

## Simplify log

- **Repos éligibles touchés** : `api-mail` seul. `dtos-mss` : porteur de contrat
  → jamais simplifié (et sa branche est vide de toute façon). Aucun frontend
  touché.
- **Commit** : `ee095f1` refactor(mail): passe qualité sur le code frais
- **Re-validation** : build 0 erreur / 0 avertissement ; **3 399 tests verts,
  0 échec** (filet anti-régression — la passe qualité ne change pas le
  comportement). Aucun rollback.

### Ce qui a été simplifié

| Axe | Fichier | Avant → après |
|---|---|---|
| Simplification | `MailServerSolicitationRecorder` | `lock` + `List<string>` + champ `_gate` → `ConcurrentQueue<string>`. Le verrou manuel et le champ de garde disparaissent, trois membres deviennent des expressions, la garantie de ne perdre aucun incrément est la même. |
| Réutilisation + efficacité | `MailRepository.SaveMailContentAsync` | l'existence d'un contenu se lisait dans une **seconde** requête ; elle se lit désormais dans la **même** que le message, via la projection légère `Select(m => new { m.Id, ContentCount = m.MailContents.Count })` — l'idiome déjà employé par `TryResolveExistingMailAsync` juste au-dessus dans ce fichier. **2 requêtes au lieu de 3** sur un chemin appelé à chaque ouverture froide. |

### Ce qui a été examiné et laissé tel quel

- **Les 6 appels `Record(MailServerCommands.X, GetEmailContentOperation)`** dans
  `ImapService` : un helper privé économiserait ~20 caractères par ligne mais
  masquerait la famille d'opération, qui est précisément l'information utile et
  ce sur quoi on grep. L'explicite gagne — pas de churn.
- **Le découpage `GetEmailContentAsync` / `…CoreAsync`** : le `try/finally` du
  premier existe pour n'apposer l'étiquette de trace qu'en **un seul point**
  malgré les huit retours du chemin. Le fusionner rendrait les huit retours
  responsables du marquage — l'inverse d'une simplification.
- **`HasDisplayableContent`** : quatre conditions, chacune nommée dans la
  documentation par ce qu'elle protège. Rien à factoriser sans perdre le
  pourquoi.
- **Étape suivante** : `/sonar task-222` (api-mail touché).

## Lint / verify-visual log

Les trois étapes frontend **skippent proprement** : `**Repos**: api-mail` et
`**Single frontend**: true` — la US corrige un chemin d'accès backend et ne
change pas la réponse de l'API, donc aucun frontend n'a été touché.

| Étape | Verdict | Constat |
|---|---|---|
| `/lint-angular` | **skip** | `Client/Angular` est sur `feature/nova-rewriting-mss` avec deux fichiers modifiés non commités (`front/apps/mss/src/environments/environment.ts`, `front/apps/weda2/src/environments/environment.ts`). **Ce sont des travaux en cours de l'humain, pas de task-222** : la forge n'a écrit aucune ligne d'Angular sur cette task. Lancer la passe lint reviendrait à retoucher le WIP de l'humain — on s'abstient et on le dit, plutôt que de laisser le tronc sale déclencher un lint qui ne nous appartient pas. |
| `/lint-mobile` | **skip** | `Client/Mobile` sur `develop`, arbre propre, aucun diff vs `origin/develop`. `client-mobile` n'est pas listé dans `**Repos**:` — `/start` n'y a donc créé aucune branche, conformément au filet de sécurité désactivé. |
| `/verify-visual` | **skip** | Aucun écran mobile touché : rien à capturer, aucune référence Stitch à apparier. |

## Sonar log

Mode A (chaîné), 2 itérations, projet `healthplatform`, branche
`fix/task-222-open-enriched-mail-no-imap`.

### KPIs qualité — baseline → final

| Métrique | Baseline (avant task-222) | Final | Cible LT |
|---|---|---|---|
| Bugs | 1 | **1** | 0 |
| Vulnerabilities | 0 | **0** | 0 ✓ |
| Security Hotspots (à revoir) | 1 | **1** | 0 |
| Code Smells | 18 | **18** | — |
| Coverage | 86,9 % | **87,0 %** | ≥ 95 % |
| Duplication | 0,5 % | **0,5 %** | — |
| Reliability rating | C | **C** | A |
| Security rating | A | **A** | A ✓ |
| Maintainability rating | A | **A** | A ✓ |
| ncloc | 41 266 | 41 478 | — |
| **Quality Gate** | ERROR | **ERROR** | OK |

### Zero-new-debt : tenu

| Itération | Finding new-code attribuable à task-222 | Action |
|---|---|---|
| 1 | `csharpsquid:S125` (code commenté) — `IMailRepository.cs:66` | corrigé, `1c2b24c` |
| 2 | **aucun** | — |

Le finding était un **faux positif de forme** : le bloc de commentaire
documentant le contrat de `SaveMailContentAsync` cite `(folderPath, uid)`,
`MailContent`, `GetMailAsync` et termine ses puces par des points-virgules —
Sonar l'a lu comme du code mis en commentaire. Converti en commentaire de
documentation XML (`<summary>` / `<remarks>` / `<returns>` avec une `<list>`),
ce qui est de toute façon la forme attendue sur un membre d'interface :
`MailRepository.SaveMailContentAsync` y renvoyait déjà par `<see cref>`.

**Après correction : zéro finding new-code sur le code de task-222.**

### Le Quality Gate est ERROR, et ce n'est pas task-222

Il faut le dire nettement plutôt que de laisser la couleur parler : le QG est en
`ERROR` sur `new_violations = 18 > 0` et
`new_security_hotspots_reviewed = 83,3 % < 100 %`, et **aucune de ces
18 violations n'appartient à task-222**. Provenance vérifiée une par une :

| Origine | Fichiers | Count |
|---|---|---|
| **task-220** (harnais de mesure `journey`) | `tests/loadtest-k6/report.py`, `scenarios/journey.js`, `lib/journey-model.js` | 16 (dont l'unique `BUG`, `python:S1244`, et l'unique hotspot `javascript:S2245`) |
| **antérieur à la forge** | `src/Infrastructure/Repository/BaseRepository.cs:68`, `src/Application/Services/Interfaces/IIheXdmProcessingService.cs:9` (`csharpsquid:S103`) | 2 |
| **task-222** | — | **0** |

C'est exactement le piège déjà connu : la *new-code period* du projet est une
baseline large, elle englobe donc des tasks **déjà mergées**. Un QG rouge n'y
signifie pas « cette task a introduit de la dette ». Les 9 `S3776` (complexité
cognitive) relèvent par ailleurs de `/sonar-s3776`, hors chaîne autonome par
construction (1 méthode = 1 PR), et les findings Python/JS du harnais de charge
ne sont pas du code produit.

**Aucun de ces 18 n'a été touché** : les corriger serait sortir du scope de la
US et gonfler une PR de correctif de performance avec du nettoyage de harnais.
Best-effort assumé, findings restants acceptés — et nommés, pas passés sous
silence.

### Note pour `conventions/csharp.md`

Entrée `S125` ajoutée : sur un **membre d'interface**, documenter le contrat en
commentaire `//` multi-ligne se fait signaler dès que le texte cite des
identifiants et ponctue en `;`. Écrire d'emblée un commentaire de documentation
XML — c'est la forme attendue à cet endroit, et elle est visible à l'appel.

- **Étape suivante** : `/review task-222`

## PRs

- `api-mail` : **https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/150**
  — label `awaiting-human-merge`
- `dtos-mss` : **aucune PR** — aucun changement de contrat, la branche
  `fix/task-222-open-enriched-mail-no-imap` créée par `/start` est restée sans
  commit (comportement documenté de l'auto-inclusion `dtos-mss`).
- `client-angular`, `client-mobile`, `client-blazor` : non concernés
  (`**Single frontend**: true` — la réponse de l'API est inchangée).

## Code Review Summary

**Verdict : APPROVED** — 12 fichiers revus, 1 remarque non bloquante, 0 bloquant.

| Zone | Verdict |
|---|---|
| `ImapService.GetEmailContentAsync` + helpers | ✅ le stock reste la voie rapide ; l'écriture en retour se fait **hors du verrou de session**, donc n'allonge pas la détention — précisément la grandeur que la campagne avait pointée |
| `MailRepository.SaveMailContentAsync` | ✅ identité `(dossier, uid, génération)` alignée sur `GetMailAsync` ; projection légère (2 requêtes, pas 3) reprenant l'idiome de `TryResolveExistingMailAsync` |
| `MailServerSolicitationRecorder` | ✅ `ConcurrentQueue`, aucun verrou ; étiquettes littérales uniquement |
| `ImapConnectionService` | ✅ ne compte que les connexions/authentifications réellement émises — une session reprise du pool ne parle pas au serveur |
| Sécurité / PGSSI-S | ✅ aucune donnée de santé dans les logs ajoutés ni dans les étiquettes de métrique ; `EnableSensitiveDataLogging` absent du repo (vérifié) donc aucune valeur de paramètre SQL dans les exceptions journalisées |
| Architecture | ✅ le contrat vit dans `IMailRepository` (couche Application), l'implémentation EF dans Infrastructure ; aucun type EF ne fuit |
| Tests | ✅ 12 tests neufs ; assertions sur un **nombre** de sollicitations, jamais sur un temps |

### ⚠️ Remarque non bloquante — fenêtre TOCTOU sur l'écriture en retour

`IX_MailContents_MailId` n'est **pas** unique : deux ouvertures froides
simultanées du même message par deux sessions client du même praticien (le verrou
de session est par `(email, ClientSessionId)`, il ne les exclut pas) peuvent
insérer deux lignes de contenu.

**Conséquence bornée** — les deux portent le **même** corps (un message d'UID
donné est immuable dans sa génération), la lecture prend la dernière, aucune
donnée fausse n'est affichée, aucune exception n'est levée, suppression en
cascade avec le message. La voie d'enrichissement porte la même fenêtre,
documentée par `TryResolveExistingMailAsync`.

**Pourquoi ce n'est pas corrigé ici** : la supprimer demande un index unique,
donc une migration **avec dé-doublonnage des lignes existantes** — une task à
part entière, pas un ajout discret dans un correctif de performance, et aucun
test de cette PR n'exercerait la concurrence réelle qui la déclenche. Consignée
en commentaire dans le code (`76ba6d3`) pour qu'elle soit pesée et non
redécouverte. **Candidate à une US dédiée.**

### Validation

| | Résultat |
|---|---|
| Build (`dotnet build`) | ✓ 0 erreur, 0 avertissement |
| Tests (`dotnet test`) | ✓ **3 399 réussis, 0 échec**, 16 ignorés d'avance |
| Sync `develop` | ✓ `Already up to date` (merge, pas rebase) |
| DOD | 9/11 vérifiés ; **2 critères de banc déférés au HAG** (nœud distant absent + rapport de référence absent de la machine — détail dans le `## Develop log`) |

---

## ⛔ Correction du 2026-08-04 — tout ce qui précède sur le correctif est FAUX

> **Cette section prévaut sur les sections `## Develop log`, `## Simplify log`,
> `## Sonar log`, `## PRs` et `## Code Review Summary` ci-dessus.** Elles sont
> conservées telles quelles, non corrigées, parce que c'est leur raisonnement
> qu'il faut pouvoir relire pour comprendre comment une cause cohérente a été
> bâtie sur un artefact de mesure. Ne pas s'y fier pour l'état de la task.

**Défaut trouvé par l'humain en relecture, avant tout merge.**

### 1. Le correctif était dangereux — retiré (`5da54bc`)

L'écriture en retour du contenu depuis `GetEmailContentAsync` **empoisonnait le
marqueur d'enrichissement**. L'existence d'une ligne `MailContents` signifie
« ce message a été analysé » partout dans le code : `GetEnrichedUidsAsync`
(`MailContents.Any()`) consommé par `ComputePendingEnrichmentAsync`
(`ImapService:827`) et `BackgroundImapService:142` ; `TryResolveExistingMailAsync`
(`ContentCount > 0` ⇒ « already enriched — skipping », **avant** la promotion) ;
`GetCoverageCountsAsync` pour l'indicateur produit.

Conséquence : le médecin ouvre un message pas encore analysé — **flux voulu**, le
frontend affiche les premiers éléments puis déclenche `POST …/emails/enrich` —, une
ligne corps-seul est posée, l'analyse écarte le message, **le CDA n'est jamais
décodé** (aucun document médical, aucun rattachement patient, aucun résultat de
biologie, aucun embedding), et `NotifyAlreadyEnrichedAsync` annonce au frontend
que c'est terminé : il cesse d'attendre. **Perte de contenu clinique,
silencieuse.**

Retiré aussi `HasDisplayableContent` : je l'avais justifié par un « écran blanc
définitif » que je n'ai jamais établi.

### 2. Le diagnostic est invalidé, pas seulement le correctif

Le scénario `journey` **n'appelle jamais l'enrichissement** — c'est écrit dans son
code — et chauffe sa bande de relecture par `getEmailContent`, en commentant à
tort que « le GET contenu matérialise le `MailContent` ». L'étape 3 « ouvrir un
message enrichi (servi base) » mesurait donc des messages **jamais analysés** : un
fetch IMAP complet, comportement normal et attendu.

D'où l'égalité 440 ≈ 442 ms qui fondait la US. Et les 34 ms de la pièce jointe ne
prouvent rien contre le produit : les pièces jointes sont des **octets** mis en
cache, sans sémantique d'enrichissement.

**Le dépassement de l'étape 3 n'est donc pas un défaut produit établi**, et le
verdict du rapport du 2026-08-03 sur cette étape est **non opposable** tant que le
harnais n'enrichit pas sa bande chaude.

### 3. Ce qui reste livré et mergeable

| Élément | État |
|---|---|
| Décompte des sollicitations du serveur (métrique + trace + service `Scoped`) | **conservé** — aucun changement de comportement |
| Conversion en doc XML du contrat (S125) | conservé |
| Écriture en retour du contenu, `HasDisplayableContent`, 8 tests associés | **retirés** |
| Garde-fous anti-réintroduction (2 avertissements en code + 1 test d'intégration) | ajoutés |

Build 0 erreur / 0 avertissement, **3 389 tests verts** (1 flaky `Services/Export`
pré-existant, hors diff, vert en isolation).

### 4. DOD — état réel

| Critère | État |
|---|---|
| Build / tests | ✓ |
| Décompte des sollicitations instrumenté | ✓ |
| Cause des ~440 ms close | ⛔ **non** — la cause supposée était un artefact de mesure ; la vraie question est rouverte |
| Tests unitaires du chemin corrigé | ⛔ sans objet — il n'y a plus de correctif |
| Test d'intégration « ne sollicite plus le serveur » | ⚠️ requalifié : prouve qu'un message **enrichi** est servi sans sollicitation (ce qui était déjà vrai avant la task) |
| Tir `journey` K=1, étape 3 ≤ 100 ms | ⛔ non exécutable, et **non certifiable** avant correction du harnais |
| Non-régression sur les 7 autres étapes | ⛔ non exécuté |
| Comportement en cas de contenu périmé tranché | ⚠️ sans objet — plus d'écriture en retour |
| Aucune donnée de santé dans les logs ajoutés | ✓ |
| Cloisonnement praticien préservé | ✓ (aucune écriture) |

**La US n'est pas satisfaite** — et il n'est pas établi qu'elle doive l'être.

### 5. Arbitrage attendu

Trois questions dans **`questions/task-222.md`** : fermer / re-cadrer / maintenir
task-222 ; qui corrige le harnais (task-224 ?) ; faut-il une US pour la lacune de
couverture ouverture → enrichissement, qui est ce qui a laissé passer le défaut.

- **Étape suivante** : décision PO. La task repasse en `wip-*` ; la PR #150 reste
  ouverte, retitrée sur le seul périmètre réellement livré.
