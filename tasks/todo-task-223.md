# todo-task-223.md — Un message parti ne doit jamais être annoncé en échec au médecin

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune stricte. **Interaction à connaître avec task-216**
(retrait de la voie d'écriture d'archivage) : ce retrait réduira beaucoup la
**fréquence** du défaut, mais **ne le supprime pas** — le défaut est dans le
mécanisme de libération du verrou de session, pas dans la voie d'écriture. Les
deux US sont indépendantes et peuvent être menées dans n'importe quel ordre ;
celle-ci ne doit pas être classée sans suite si task-216 passe d'abord.
**Priorité**: **1** — c'est le seul des trois constats de la campagne du
2026-08-03 qui **trompe le médecin** : il lit « échec » sur un message que son
correspondant a bien reçu. Rare, mais la conséquence est une duplication de
document de santé chez le destinataire.

## Objective

Qu'un envoi remis au destinataire soit **toujours** annoncé comme réussi au
médecin, même quand une étape secondaire (l'archivage dans les messages
envoyés) échoue.

## Le constat — mesuré

Campagne de certification du **2026-08-03** (200 médecins, rythme réel,
3 352 envois) : **un envoi sur 3 352 a été rendu au médecin en erreur alors
que le message était parti et remis**. C'est la seule erreur de toute la
campagne — 105 000 requêtes, taux d'erreur global 0,001 %.

Ce qui s'est réellement passé sur cet envoi (trace
`4ad7594f36b4773d8551b77ba08fc663`, rapport
`reports/2026-08-03/report-journey-certif-n200-180029.md`) :

1. le message **est envoyé et remis** — l'envoi lui-même réussit ;
2. l'archivage dans le dossier des messages envoyés échoue ;
3. **cet échec-là est déjà traité comme non fatal** par le code — il n'est pas
   la cause de l'erreur rendue ;
4. c'est **la libération du verrou de session, à la sortie de l'archivage**,
   qui lève une exception non rattrapée (`SemaphoreFullException`) et transforme
   le tout en erreur serveur.

Mécanisme établi par lecture du code et par élimination : le verrou est relâché
**en retrouvant la session par son identifiant**, et non en relâchant celui qui
a effectivement été pris. Si l'entrée de session est recyclée pendant
l'opération, la libération tombe sur un verrou neuf et lève. L'archivage passe
par une **voie de session dédiée** (task-213) qui n'existe que le temps des
envois : c'est elle qui est la plus exposée à ce recyclage, ce qui explique la
localisation et la rareté. Détail complet dans la section « Analyse Seq » du
rapport cité.

## Pourquoi la conséquence est plus grave que sa rareté

Le médecin voit « échec d'envoi » sur un compte rendu **effectivement remis**.
Le geste naturel est de **le renvoyer** : le destinataire reçoit alors **deux
fois le même document de santé**, sans moyen simple de savoir lequel est le bon.
Dans une messagerie de santé, un document dupliqué dans le dossier d'un patient
n'est pas un désagrément d'ergonomie.

## Ce qu'il ne faut PAS présumer

- **Ne pas se contenter d'avaler l'exception.** Rendre l'envoi « réussi » en
  masquant la panne de libération laisserait un verrou dans un état indéterminé.
  Les deux choses sont à traiter : **le mécanisme de libération** (qu'il ne
  puisse pas se tromper de verrou) **et** la robustesse (qu'un défaut de
  comptage ne devienne jamais une erreur rendue au médecin).
- **Ne pas présumer que task-216 règle le sujet.** Le retrait de la voie
  d'écriture réduit l'exposition ; le mécanisme fautif reste. Si task-216 passe
  d'abord, cette US garde tout son objet — mais sa **reproduction** au banc
  devient plus difficile, ce que le plan de test doit assumer.
- **Ne pas transformer un échec d'archivage en succès silencieux.** Le médecin
  doit être informé que son message est parti **et** que sa copie dans les
  messages envoyés manque : ce sont deux informations distinctes, et la seconde
  a une valeur d'imputabilité (retrouver ce qu'on a envoyé, et à qui).
- **Ne pas élargir au verrou de session en général.** Sa portée et son
  existence sont des sujets ouverts depuis task-211/213/216 ; ici on corrige un
  défaut de **libération**, pas le modèle de verrouillage.

## Contenu attendu

1. **Le mécanisme de libération rendu incapable de se tromper de verrou** —
   quelle que soit la vie de l'entrée de session pendant l'opération.
2. **Une libération défensive** : un défaut de comptage se journalise et
   n'atteint jamais le médecin sous forme d'erreur.
3. **La distinction rendue au médecin** entre « message parti » et « message
   parti mais non archivé », et la trace correspondante côté exploitation.
4. **Un test qui reproduit le scénario** — recyclage de l'entrée de session
   pendant l'opération d'archivage — et qui échoue avant le correctif.

## Hors scope

- La portée du verrou de session, son existence, la voie d'écriture (task-211,
  task-213, **task-216**).
- Les autres dépassements SLO de la campagne (**task-222**, et l'étape 8).
- L'outillage de mesure (**task-224**).

## Definition of Done

- [ ] Build passe (0 erreur)
- [ ] Tests passent (0 échec)
- [ ] Test unitaire reproduisant le **recyclage de l'entrée de session pendant
      l'archivage**, constaté **ROUGE avant** le correctif (preuve dans le
      `## Develop log`)
- [ ] Test unitaire : un défaut de libération du verrou **ne remonte jamais** en
      erreur serveur au médecin
- [ ] Test unitaire / intégration : envoi remis + archivage en échec ⇒ le médecin
      reçoit un **succès**, et l'absence d'archivage est **journalisée** de façon
      distinguable
- [ ] Aucune régression sur le chemin d'envoi nominal (envoi + archivage OK)
- [ ] Évènement PGSSI-S d'envoi toujours journalisé, avec la distinction
      « archivé / non archivé »
- [ ] Aucune donnée de santé en clair dans les traces ajoutées (contenu du
      message, INS, RPPS dans les sujets)
- [ ] Tir `journey` **K=1** au banc : **zéro erreur serveur sur l'envoi**
      (la campagne de référence en avait 1 sur 3 352)

## Manual Test Plan

```bash
# Banc distant, campagne d'envoi soutenue au rythme réel
cd Api/Mail
MSS_LOADTEST_MAIL_HOST=<ip-noeud> dotnet run --project src/AppHost --launch-profile https-load-test
dotnet run --project tests/mss.mail.loadtest.seed -- --users 200 --messages 150 \
  --api http://127.0.0.1:5052 --mail-host <ip-noeud> --latency 95
export BYPASS_KEY=loadtest-local-only MSS_LOADTEST_MAIL_HOST=<ip-noeud>
# part d'envoi relevée pour multiplier les occasions, fenêtre longue
LATENCY_MS=95 USERS=200 MESSAGES_PER_USER=150 JOURNEY_P_SEND=0.8 \
  JOURNEY_STAGES="200:35m" JOURNEY_TIME_COMPRESSION=1 \
  tests/loadtest-k6/run.sh journey
tests/loadtest-k6/report.sh <dernier json> --expected 0
```

**Ce que l'humain doit voir** :
- dans le rapport, **taux d'erreur 0,00 %** et le check « send: accepted »
  à **100 %** (la campagne du 2026-08-03 était à 99,963 %) ;
- dans Seq sur la fenêtre du tir : **aucune** `SemaphoreFullException`, et
  **aucune** erreur serveur sur `/mail/sendmail` ;
- dans le client, sur un envoi dont l'archivage échoue (à provoquer en retirant
  le dossier des messages envoyés de la boîte de test) : le médecin voit son
  message **parti**, avec une mention distincte indiquant que la copie dans les
  messages envoyés manque — et le message est bien présent chez le destinataire ;
- côté serveur de messagerie, le message est bien remis au destinataire.

**Données de test** : boîtes `loadtest-*`, corpus synthétique, aucune donnée de
santé réelle, destinataire = puits de test.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — messagerie MSSanté du praticien.
- **Vague Ségur** : hors vague — correction d'un défaut de restitution sur un
  geste déjà référencé ; aucun contrat d'interopérabilité modifié.
- **Exigences DSR honorées** : aucune nouvelle. La US **restaure** en revanche la
  fiabilité de l'information rendue au PS sur l'aboutissement de son envoi, qui
  conditionne l'imputabilité de l'échange.
- **INS** : non manipulée — le défaut est dans la libération d'un verrou
  technique, en aval de toute logique patient.
- **Authentification PS** : inchangée (PSC / e-CPS pour l'envoi MSSanté, niveau
  eIDAS substantiel au moins). Rappel du garde-fou : un envoi MSSanté n'est
  jamais autorisé sur simple mot de passe.
- **Habilitations** : inchangées.
- **Interop CI-SIS** : MSSanté (volet transport). Le message émis n'est pas
  modifié par cette US — ni son contenu, ni ses en-têtes, ni son enveloppe.
- **MSSanté** : adresse émettrice et certificat IGC Santé inchangés. ⚠️ **Le
  garde-fou « jamais de RPPS dans les sujets ou en-têtes » s'applique aux
  traces ajoutées** : l'adresse seule identifie l'émetteur.
- **Tracé PGSSI-S** : évènement « envoi d'un document de santé par un PS »
  — **à enrichir** d'une issue distinguant « remis et archivé » de « remis, non
  archivé ». Durée de conservation inchangée. C'est cette trace qui permettra au
  support de trancher, sans que le médecin ait à renvoyer.
- **Consentement patient** : non applicable — échange entre professionnels dans
  le cadre de la prise en charge.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui en production (le message est une DSCP). Banc local
  et synthétique.
- **AIPD / impact RGPD** : inchangé — pas de nouveau traitement ; l'enrichissement
  de trace porte sur l'issue technique de l'envoi, pas sur son contenu.
