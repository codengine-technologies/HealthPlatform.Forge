# todo-task-268.md — Deux chemins de lecture comptent les fils différemment : une conversation initiée par le praticien est visible sur l'un, invisible sur l'autre

**Repos**: api-mail
**Epic**: E009
**Single frontend**: true
**Dependencies**: aucune. **task-194** (`todo`) **préserve délibérément** la
divergence décrite ici, pour rester une pure task de performance — elle ne
tranche pas, elle isole. Celle-ci tranche. Les deux sont livrables dans
n'importe quel ordre ; si task-194 passe d'abord, celle-ci s'applique sur du
code déjà borné, ce qui la rend plus simple.
**Priorité**: **2** — défaut **fonctionnel** visible par le médecin, sur une
fonctionnalité livrée. Ce n'est pas de la performance : un compteur affiche deux
valeurs différentes selon le chemin qui a servi la page.

> **Origine** : constat du 2026-08-20, en instruisant task-194 sur demande
> humaine (« comment es-tu certain de ne pas provoquer de régression ? »).
> Rattaché à **E009** (messagerie sécurisée) et non à E011 : c'est le
> comportement affiché au praticien qui est en cause, pas un coût.

## Objective

Qu'un fil de discussion soit compté **de la même façon** quel que soit le chemin
de lecture qui a servi la page — et que la règle retenue soit celle qui rend
service au médecin.

## Ce qui est établi — état du code au 2026-08-20

Il existe **deux** implémentations du comptage de fils, atteintes par deux
chemins de lecture différents, et **elles ne comptent pas la même chose** :

| | `GetThreadCountsAsync` (`MailRepository.cs:4039`) | `GetMailsByUidsAsync` (`~:1600`, task-247) |
|---|---|---|
| Chemin | `OnlineMailDataProvider` — lecture **IMAP** | lecture servie par la **base** |
| Dossier `Sent` | **exclu** (`!ILike(FolderPath, "Sent")`) sur les deux requêtes | **inclus**, délibérément |
| Justification écrite dans le code | aucune | « Un fil TRAVERSE les dossiers : la racine d'une conversation vit couramment dans `Sent` pendant que les réponses arrivent en `INBOX`. » |

### Le cas concret, et il n'est pas marginal

Une conversation que le **praticien a initiée** : il écrit le premier message
(racine → dossier `Sent`), le correspondant répond (réponse → `INBOX`).

- Chemin **base** : racine comptée + 1 réponse = **2** → le fil s'affiche,
  badge « 2 messages ».
- Chemin **IMAP** : racine exclue, total = 1, **sous le seuil de 2** → le fil
  n'apparaît pas du tout. La réponse s'affiche comme un message isolé.

Le seuil de 2 (`if (totalCount >= 2)`) transforme donc une différence de +1 en
**disparition complète** du fil. Ce n'est pas un écart d'affichage d'un
compteur : c'est un fil qui existe ou n'existe pas selon le chemin.

### Ce qui n'est pas établi, et qu'il faut mesurer

- **Quelle est la fréquence réelle du cas ?** Une conversation initiée par le
  praticien est un geste courant en MSSanté (demande d'avis, envoi d'un compte
  rendu suivi d'une réponse), mais la proportion sur une vraie boîte n'est pas
  chiffrée.
- **Quand chaque chemin sert-il la page ?** `OnlineMailDataProvider` vs lecture
  base : la bascule dépend du mode de connexion (`IConnectionModeService`). Il
  faut établir **quel chemin sert le cas courant** avant de décider lequel
  aligner sur l'autre — aligner le chemin rare sur le chemin courant n'a pas le
  même effet que l'inverse.
- **Y a-t-il d'autres divergences que `Sent` ?** Les deux implémentations ont
  divergé dans le temps ; `Sent` est celle qui a été constatée, pas
  nécessairement la seule. Un inventaire est attendu.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que l'exclusion de `Sent` est un oubli.** Elle est peut-être
  intentionnelle : compter la racine dans `Sent` fait apparaître, dans la boîte
  de réception, des fils dont le premier message n'y est pas. C'est défendable
  dans les deux sens — c'est précisément pourquoi cette US existe au lieu d'un
  correctif direct.
- **Ne pas présumer que l'inverse est un oubli non plus.** task-247 a écrit
  l'inclusion **délibérément**, avec un test de verrouillage
  (`GetMailsByUidsAsyncCountsAThreadWhoseRootLivesInAnotherFolder`). Casser ce
  test sans décision serait annuler un arbitrage antérieur par accident.
- **Ne pas présumer que « unifier » veut dire « supprimer le filtre ».** Les deux
  directions sont ouvertes : inclure `Sent` partout, ou l'exclure partout. La
  seconde ferait **disparaître** des fils aujourd'hui visibles sur le chemin
  base — une régression pour un utilisateur qui les voit déjà.
- **Ne pas présumer que le seuil de 2 est hors sujet.** C'est lui qui amplifie
  l'écart de +1 en disparition. Toute décision sur `Sent` doit énoncer son effet
  combiné avec ce seuil.
- **Ne pas présumer que deux implémentations doivent rester deux.** La vraie
  cause de la divergence est la duplication. Convergence de comportement et
  convergence de code sont deux questions ; la seconde peut être différée, la
  première non.

## Ce que la US doit livrer

1. **Un inventaire des divergences** entre les deux implémentations — pas
   seulement `Sent` : périmètre de dossiers, seuil, déduplication, sensibilité à
   la casse, traitement des racines absentes. Un tableau, pas une prose.
2. **Une règle unique, énoncée en langage métier** : « un fil compte les messages
   qui … , où qu'ils se trouvent, sauf … ». Elle doit être compréhensible par le
   PO, pas seulement par le code.
3. **Les deux chemins appliquent cette règle** et rendent des compteurs
   identiques sur le même jeu de données.
4. **Les cas qui changent d'affichage sont listés nommément**, avec leur sens
   pour le médecin — « avant : ce fil n'apparaissait pas / après : il apparaît
   avec N messages ». Un changement de comportement non listé est un défaut.
5. **Un garde-fou contre la re-divergence** : un test qui exerce **les deux**
   chemins sur le même jeu de données et exige l'égalité des compteurs. C'est le
   seul livrable qui empêche le problème de revenir, et il vaut plus que le
   correctif lui-même.
6. **Si la convergence de code est retenue** (une seule implémentation), elle est
   un bonus, pas l'objectif — l'objectif est l'égalité de comportement, prouvée.

### Hors scope

- **Le coût du comptage** → task-194. Ne pas optimiser ici.
- **Le gating du calcul** → task-266.
- **La correspondance par sous-chaîne sur `References`** (plus correcte par jeton
  au sens RFC 5322) : c'est une troisième question, elle changerait aussi les
  compteurs, et elle mérite sa propre US si elle est confirmée.
- Le regroupement visuel des fils côté client : inchangé, les clients consomment
  les mêmes champs.

## Definition of Done

- [ ] Build passe (`dotnet build HealthPlatform.Api.Mail.sln`, 0 erreur)
- [ ] Tests passent (0 échec, hors flaky pré-existants documentés)
- [ ] **Inventaire des divergences** consigné dans la task, sous forme de tableau,
      établi par lecture des deux implémentations — pas par supposition
- [ ] **La règle retenue est écrite en une phrase métier** dans la task, et
      l'arbitrage qui l'a choisie est daté et attribué
- [ ] Test : sur un même jeu de données, les deux chemins rendent des compteurs
      **identiques** — le garde-fou anti-re-divergence, exerçant réellement les
      deux chemins
- [ ] Test : le cas « racine dans `Sent`, réponse en `INBOX` » a le comportement
      décidé, sur **les deux** chemins
- [ ] Test : le cas « même `MessageId` dans plusieurs dossiers » reste compté en
      lignes (non-régression de task-247, mesurée 3 → 2 à l'époque)
- [ ] Le test de verrouillage de task-247
      (`GetMailsByUidsAsyncCountsAThreadWhoseRootLivesInAnotherFolder`) est
      **toujours vert**, ou son changement est justifié explicitement dans la task
- [ ] **Liste nommée des cas dont l'affichage change**, avec avant/après, dans la
      task et recopiée dans le body de la PR — c'est ce que l'humain valide au HAG
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

1. Démarrer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. Démarrer le front legacy : `cd Client/Angular/front && npm start`
3. Se connecter avec une boîte de test MSSanté de formation.
4. **Construire le cas** : depuis l'application, **envoyer** un message à une
   seconde boîte de test (la racine part dans `Sent`), puis **répondre** depuis
   cette seconde boîte. La première boîte a maintenant une réponse en `INBOX`
   dont la racine est dans son `Sent`.
5. Passer le mode d'affichage sur **« Conversation »**, ouvrir la boîte de
   réception. **Attendu** : le comportement **décidé par la US**, et surtout
   **le même** que celui observé à l'étape 7.
6. Noter ce qui s'affiche : le fil apparaît-il ? avec quel compteur ?
7. **Forcer l'autre chemin de lecture** (bascule du mode de connexion, cf.
   `IConnectionModeService`), recharger la même boîte de réception.
   **Attendu** : **exactement** le même affichage qu'à l'étape 6. C'est le seul
   point qui compte dans ce plan de test.
8. Répéter avec un fil plus long (3 messages, dont la racine dans `Sent`).
9. Contre-épreuve de non-régression : un fil entièrement contenu dans `INBOX`
   doit être compté à l'identique avant/après, sur les deux chemins.

**Données de test** : boîtes de formation MSSanté, aucun patient réel, aucun INS.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : V2 — correctif de cohérence d'affichage sur le volet MSSanté
  existant ; aucune exigence DSR nouvelle
- **Exigences DSR honorées** : MSSanté — restitution cohérente d'un échange de
  messages ; aucune exigence nouvelle adressée
- **INS** : non applicable — le comptage de fils repose sur les en-têtes
  RFC 5322 (`Message-Id`, `In-Reply-To`, `References`), jamais sur l'identité du
  patient
- **Authentification PS** : PSC / e-CPS, niveau eIDAS substantiel — inchangée
- **Habilitations** : inchangées. **Point de vigilance** : la règle retenue ne
  doit **jamais** faire apparaître dans une boîte un message appartenant à une
  autre boîte. Le périmètre reste la base du praticien
- **Interop CI-SIS** : non applicable — aucun format d'échange métier touché
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — cible inchangée
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau, aucun élargissement
  de périmètre de données
