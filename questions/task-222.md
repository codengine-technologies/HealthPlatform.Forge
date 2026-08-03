# questions/task-222.md — la prémisse de la US ne tient pas, et le correctif était dangereux

**Date** : 2026-08-04
**Task** : task-222 — « Ouvrir un message déjà analysé ne doit plus repayer le trajet vers le serveur de messagerie »
**Épic** : E015
**Soulevé par** : l'humain, en relecture du correctif proposé
**État** : 🚫 **task-222 ANNULÉE le 2026-08-04.** Ce fichier reste le dossier
d'instruction du défaut évité — il ne décrit plus une US en cours.

---

## 🚫 Décision finale du 2026-08-04 — task-222 annulée

Deux décisions successives le même jour :

1. **« recadre task-222 sur la mesure et confie le harnais à task-224 »** —
   appliquée (recadrage de la US, défaut 5 ajouté à task-224).
2. **« je souhaite supprimer 222, la branche et la PR ; à la place crée une
   nouvelle tâche pour ajouter l'instrumentation »** — **c'est la décision qui
   prévaut**.

**Motif de l'annulation** : trop de modifications non maîtrisées sur une seule
branche — un correctif applicatif retiré, une passe de simplification, un
refactoring du chemin d'ouverture et l'instrumentation. Un périmètre qu'on ne
remet pas sous contrôle en le rapiéçant, même après le revert.

**Exécuté** : PR `api-mail` #150 **fermée sans merge** ; branches
`fix/task-222-open-enriched-mail-no-imap` **supprimées** (locales et distantes)
sur `api-mail` et `dtos-mss` ; task déplacée en
`tasks/archived/archived-task-222.md` avec bandeau d'annulation. **Aucune ligne
de task-222 n'est sur `develop`.**

**Repris** :

| Acquis | Repris par |
|---|---|
| Le décompte des sollicitations du serveur | **task-225** — écrite **strictement bornée** : son « Hors scope » interdit explicitement tout correctif, toute modification du dépôt, toute passe de simplification, et son DOD plafonne le diff (2 fichiers neufs + 4 touchés) |
| L'artefact de mesure de l'étape 3 | **task-224**, défaut 5, priorité 3 → 2 |
| Les garde-fous contre le défaut évité | **task-225**, points 4 et 5 du contenu attendu |

> ### La leçon de forme, et elle est pour moi
>
> Le correctif dangereux n'est pas le seul problème : c'est le **mélange** qui a
> rendu la branche inévaluable. Un correctif applicatif, une instrumentation, un
> refactoring et une passe qualité sur la même branche, et plus rien n'est
> jugeable séparément — ni par une revue, ni par un revert propre. task-225 est
> écrite avec un contrat de périmètre explicite pour cette raison, et un critère
> de DOD qui plafonne la taille du diff.

### Décisions de cadrage antérieures (conservées pour la traçabilité)

> « recadre task-222 sur la mesure et confie le harnais à task-224 »

| Question | Décision | Appliqué |
|---|---|---|
| **Q1** — fermer / re-cadrer / maintenir task-222 ? | **Re-cadrée sur la mesure** (option b). Le décompte des sollicitations est l'objet de la US ; le correctif applicatif sort du périmètre, et n'est pas rouvert faute de défaut produit établi. | `tasks/done-task-222.md` réécrite (Objectif, DOD, Plan de test, Hors scope), DOD **satisfaite**, PR #150 recadrée |
| **Q2** — qui corrige le harnais ? | **task-224.** | `tasks/todo-task-224.md` : **défaut 5** ajouté en tête par gravité, priorité relevée **3 → 2**, 3 items de contenu attendu, 6 critères de DOD, plan de test étendu, et la ligne « aucun ne bloque task-222 » corrigée — elle était fausse |
| **Q3** — US pour la lacune de couverture ouverture → enrichissement ? | ⏳ **non arbitrée** | rien fait, volontairement — voir ci-dessous |

### Ce que la décision implique, et qu'il faut assumer

- **Aucun défaut produit n'est retenu sur l'ouverture d'un message.** Le geste
  n'est pas « corrigé » : il est déclaré **non démontré défaillant**. Rouvrir le
  sujet demandera une mesure faite après task-224.
- **Le verdict « étape 3 » du 2026-08-03 reste non opposable** jusqu'à task-224,
  qui doit l'annoter comme tel dans `reports/INDEX.md`. D'ici là, aucun tir ne
  peut certifier cette étape — ni avant, ni après un quelconque correctif.
- **task-224 devient bloquante pour un chiffrage** qu'elle ne portait pas
  auparavant. Sa priorité a été relevée en conséquence.

### Q3 reste ouverte — et c'est le point que je remonte

Aucun test ne traverse la séquence **ouverture → enrichissement**. C'est ce trou,
et non un manque de rigueur ponctuel, qui a laissé une perte de contenu clinique
franchir 3 399 tests verts jusqu'au seuil du merge.

La garde posée par task-222 est **partielle** : elle prouve qu'une lecture
n'écrit rien, donc elle bloque *ce* défaut précis. Elle ne prouve pas que la
chaîne ouverture → analyse → contenu complet fonctionne de bout en bout. Un
prochain défaut situé ailleurs sur cette chaîne passerait de la même façon.

Ce n'est ni du ressort de task-222 (instrument) ni de task-224 (outillage de
mesure) : c'est une couverture applicative, à arbitrer séparément. Recommandation :
une US dédiée, de faible coût, dont la valeur est d'interdire structurellement la
classe de défaut plutôt qu'un défaut.

---

## 1. Le correctif proposé était dangereux — retiré

`/develop` avait ajouté une **écriture en retour** du corps dans `MailContents`
depuis `GetEmailContentAsync`, par symétrie apparente avec `GetAttachmentAsync`
(qui, lui, écrit bien en retour via `UpdateAttachmentAsync`).

**La symétrie était fausse.** L'existence d'une ligne `MailContents` n'est pas un
cache de corps : c'est le **marqueur d'enrichissement** de tout le code.

| Site | Expression | Effet d'une ligne corps-seul |
|---|---|---|
| `MailRepository.GetEnrichedUidsAsync` | `MailContents.Any()` | le UID est déclaré enrichi |
| `ImapService.ComputePendingEnrichmentAsync` (:827) | `uids.Where(u => !alreadyEnriched.Contains(u))` | **le UID sort de `pendingUids`** |
| `BackgroundImapService` (:142) | idem | idem, côté synchro de fond |
| `MailRepository.TryResolveExistingMailAsync` (:177) | `ContentCount > 0` ⇒ *« already enriched — skipping re-processing »* | retour **avant** la branche de promotion |
| `MailRepository.GetCoverageCountsAsync` | `MailContents.Any()` | l'indicateur de couverture produit sur-déclare |

### Le scénario de perte

1. Le médecin ouvre un message pas encore enrichi. **C'est le flux voulu** : le
   frontend affiche les premiers éléments, puis déclenche
   `POST …/emails/enrich`, et reçoit la totalité quand le CDA est décodé.
2. L'écriture en retour posait une ligne `MailContents` **corps seul** — sans
   documents médicaux, sans résumé, sans embedding.
3. L'enrichissement voyait le message comme déjà traité ⇒ **le CDA n'était jamais
   décodé** : aucun `MailMedicalDocument`, aucun rattachement patient, aucun
   résultat de biologie, aucun embedding pour la recherche sémantique.
4. `NotifyAlreadyEnrichedAsync` annonçait au frontend que c'était terminé ⇒ il
   **cessait d'attendre**.

Perte de contenu clinique, **silencieuse**, sans aucune erreur nulle part. Sans
commune mesure avec les 440 ms visés.

**Pourquoi les 3 399 tests verts ne l'ont pas vu** : aucun ne traverse la
séquence ouverture → enrichissement. Le défaut vit dans l'interaction entre deux
chemins, chacun correct isolément. C'est une lacune de couverture à noter en soi.

**Garde-fous posés** pour que ce ne soit pas réintroduit : commentaire
d'avertissement dans `IMailRepository` à l'endroit exact où la méthode vivait,
dans la doc XML de `GetEmailContentAsync`, et un test d'intégration qui asserte
qu'**une lecture ne crée aucune ligne de contenu**.

---

## 2. Conséquence plus profonde : le constat de la US est probablement un artefact de mesure

C'est le point qui demande votre arbitrage, parce qu'il invalide le raisonnement
en amont, pas seulement le correctif.

**Le scénario `journey` n'appelle jamais l'enrichissement.** C'est écrit dans son
propre code (`tests/loadtest-k6/scenarios/journey.js`) :

```js
// Sans gravité pour CE tir — journey n'appelle jamais enrich — mais le seed
// ne doit pas être partagé avec un tir enrich/mixed sans reset-state.
```

Et sa chauffe utilise `getEmailContent` :

```js
/**
 * Premier passage d'un VU : chauffe la bande de relecture de SA boîte (le
 * GET contenu matérialise le MailContent) …
 */
```

**Cette parenthèse est fausse** — et c'est la clé. `GetEmailContentAsync`
n'écrivait rien (à raison, voir §1). La bande dite « chaude » n'était donc
**jamais enrichie**, et l'étape 3 « ouvrir un message enrichi (servi base) »
mesurait un message **jamais enrichi** : un fetch IMAP complet.

D'où l'égalité qui avait retenu l'attention du PO :

| Fait du rapport | Lecture « défaut produit » (retenue à tort) | Lecture « défaut d'instrument » |
|---|---|---|
| 440 ms (chaud) ≈ 442 ms (froid) | on jette le contenu, donc rien n'est jamais chaud | **l'étape chaude mesure du froid** |
| PJ du même message en 34 ms | asymétrie fautive entre les deux chemins | `GetAttachmentAsync` cache des **octets**, sans sémantique d'enrichissement — normal, et sans rapport |
| coût invariant à la charge | coût fixe par ouverture | idem : un fetch IMAP par ouverture |

Les deux lectures produisent **exactement les mêmes chiffres**. Une seule est
vraie, et la seconde est la plus économique : elle n'exige aucun défaut produit.

**En production, le flux est celui que vous décrivez** : ouverture → affichage
rapide → enrichissement → contenu complet. Une fois enrichi, `MailContents`
existe et la relecture **est** servie par la base — le chemin rapide fonctionne
déjà. Il n'est pas établi qu'un médecin réel paye 440 ms sur une relecture.

---

## 3. Ce qui reste livré sur la branche

| Élément | État |
|---|---|
| **Décompte des sollicitations du serveur** (`IMailServerSolicitationRecorder`, `mssante_mail_server_solicitations_total{command,operation}`, étiquette de trace `mss.mail_server.solicitations`) | **conservé** — aucun changement de comportement |
| Conversion en doc XML du contrat (S125) | conservé |
| Écriture en retour du contenu | **retiré** |
| `HasDisplayableContent` | **retiré** — justifié par un « écran blanc définitif » que je n'avais pas établi |
| 8 tests verrouillant le comportement retiré | retirés |
| 4 tests de décompte (dont 2 sur vrai PostgreSQL) | conservés, dont la garde anti-régression du §1 |

L'instrumentation garde toute sa valeur, et pas seulement pour le produit :
**c'est elle qui aurait évité cette erreur.** Une étape de banc annoncée
« servie base » qui enregistre 5 commandes IMAP ne mesure pas ce qu'elle
annonce. C'est désormais lisible dans la trace et dans Prometheus.

---

## 4. Ce que je demande d'arbitrer

**Question 1 — la US task-222 doit-elle être re-cadrée ou fermée ?**

Son objectif (« qu'ouvrir un message déjà analysé coûte le temps d'une lecture en
base ») est peut-être **déjà atteint** en production. Trois options :

- **(a) Fermer task-222**, ne garder que l'instrumentation, et rouvrir seulement
  si une campagne correctement instrumentée montre un dépassement réel.
- **(b) Re-cadrer task-222** sur ce qui reste à établir : *combien de
  sollicitations une relecture de message enrichi coûte-t-elle réellement, et
  est-ce ≤ 100 ms ?* — mesurable dès que le banc enrichit sa bande chaude.
- **(c) Maintenir task-222 en l'état** en pariant qu'un défaut produit subsiste.
  Je ne le recommande pas : rien ne l'établit aujourd'hui.

**Question 2 — qui corrige le harnais, et est-ce task-224 ?**

Pour que l'étape 3 mesure ce qu'elle annonce, `warmUpOwnMailbox` doit
**réellement enrichir** sa bande (appel `POST …/emails/enrich/sync` sur les UIDs
chauds pendant la chauffe), et le commentaire fautif doit être corrigé. Cela
touche l'outillage de mesure, que la US de task-222 place explicitement hors
scope et attribue à **task-224**. À confirmer.

Conséquence à ne pas perdre : **tant que le harnais n'enrichit pas, aucun tir ne
peut certifier l'étape 3**, ni avant ni après un quelconque correctif. Le verdict
« étape 3 au rouge » du rapport du 2026-08-03 devrait être marqué comme **non
opposable** dans l'INDEX, pour la même raison que le rapport refuse de lui-même
un verdict à rythme accéléré.

**Question 3 — la lacune de couverture ouverte-puis-enrichie mérite-t-elle une US ?**

Aucun test ne traverse ouverture → enrichissement. C'est ce trou qui a laissé
passer un défaut de perte de contenu clinique avec une suite verte. Un test
d'intégration sur cette séquence me paraît valoir plus que le correctif initial.

---

## 5. Ce que je n'ai pas fait, volontairement

- **Je n'ai pas corrigé le harnais** : hors scope de task-222 (« L'outillage de
  mesure (task-224) » est dans ses *Hors scope*), et ce serait décider à votre
  place de la question 2.
- **Je n'ai pas fermé la task** : le cadrage est une décision PO.
- **Je n'ai pas retiré l'instrumentation**, malgré l'invalidation du diagnostic :
  elle est la seule chose qui permette de trancher la question 1 par la mesure.
