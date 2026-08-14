# todo-task-260.md — L'envoi coûte 1,3 s quelle que soit la population : décomposer avant de corriger, parce que deux tentatives ont déjà échoué

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune. **task-238** a tenté deux fois de corriger ce coût et
échoué deux fois — c'est précisément l'argument pour instrumenter d'abord.
**Priorité**: **1** — **seule étape hors grille du parcours du médecin**, et
**premier poste de coût serveur** du tir à 500 (25,1 %). Tant qu'elle n'est pas
décomposée, toute correction sera écrite sur une intuition.

## Objective

Savoir **où passent les 1,3 seconde** d'un envoi de message, phase par phase, de
sorte que la prochaine US d'optimisation vise une cause mesurée.

C'est une US **d'instrument, pas d'optimisation**. Elle ne rend rien plus rapide.

## Ce qui est établi — tir `journey-500-esc` du 2026-08-14

Escalier 100 / 200 / 500 médecins, banc distant, K=1, 295 325 requêtes,
0,004 % d'erreur.

| Palier | p50 envoi | p95 envoi | Cible p50 / p95 |
|---|---|---|---|
| 100 médecins | **1 305 ms** | 1 993 ms | 1 000 / 3 000 |
| 200 médecins | **1 270 ms** | 1 963 ms | 1 000 / 3 000 |
| 500 médecins | **1 302 ms** | 2 004 ms | 1 000 / 3 000 |

**Le coût est RIGOUREUSEMENT PLAT sur un facteur 5 de population.** Ce n'est donc
pas un effet de charge, ni une file, ni une contention : c'est un **coût fixe
payé à chaque envoi**. C'est aussi ce qui rend le défaut réparable — il ne
dépend d'aucune condition de banc.

**Ce que ça pèse** : **6 085 s de temps serveur sur 4 031 appels**, soit
**25,1 %** du temps serveur total du palier 500 — le premier poste, devant le
tableau de bord (23,5 %) et la page d'en-têtes (11,5 %).

**Ce qui a déjà été fait, et n'a pas suffi** : task-231 (la connexion SMTP n'est
plus rouverte à chaque message), task-238 (la connexion retenue est entretenue,
la sonde quitte le chemin nominal), task-241 (le keep-alive agissait sur la
mauvaise horloge). Trois corrections, et le coût n'a pas bougé.

### ⚠️ La piste que l'analyse Seq désigne — à examiner en premier, pas à croire

**12 482 `SmtpCommandException` pour 4 031 envois**, soit **~3,1 par envoi** :
c'est la **famille d'exceptions la plus nombreuse de tout le tir**, devant les
extinctions de session.

Le volume suit le **nombre d'appels**, pas la charge — c'est le test que le skill
prescrit pour distinguer un coût par requête d'un incident. Rapproché d'un coût
**plat sur un facteur 5 de population**, cela désigne un chemin de code exercé à
chaque envoi, qui lève et rattrape.

⚠️ **Ce n'est PAS une cause établie.** Une exception rattrapée peut coûter très
peu, et rien ne relie aujourd'hui ces 12 482 levées aux 1,3 seconde. C'est une
**piste**, et la décomposition doit précisément permettre de la confirmer ou de
l'écarter — pas de la présumer. Une US écrite sur « il faut supprimer ces
exceptions » serait exactement l'erreur de task-222.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que c'est encore le SMTP.** Trois corrections successives ont
  visé cette hypothèse. Si elle était la bonne, le chiffre aurait bougé.
- **Ne pas présumer que c'est l'archivage dans « Messages envoyés ».** C'est le
  candidat suivant le plus évident, donc celui dont il faut se méfier — et
  `118c3f4` a déjà changé son comportement une fois.
- **Ne pas présumer que le p50 et le p95 ont la même cause.** 1,3 s au p50 contre
  2,0 s au p95 : la queue peut appartenir à une phase différente de celle qui
  domine la médiane.
- **Ne pas optimiser en passant.** Si une évidence saute aux yeux, la consigner
  comme finding et la traiter dans une US **mesurée**. Cette EPIC a annulé
  task-222 pour avoir fait l'inverse.

## Ce que la US doit livrer

Pour l'envoi, le pendant de ce que task-245 a livré pour l'enrichissement et
task-252 pour le téléchargement d'une pièce jointe : un **périmètre par envoi**,
décomposé en phases nommées, publié à côté de l'enveloppe.

Les phases à distinguer sont celles qui appellent des remèdes différents :
**obtention de la session SMTP**, **négociation TLS** si elle a lieu,
**transmission du message**, **acquittement du serveur**, **archivage dans
« Messages envoyés »**, et **le reste** par différence.

Plus le **nombre d'allers-retours vers le serveur mail par envoi** — le
dénominateur sans lequel une durée ne dit pas si elle vient du volume d'échanges
ou de leur coût unitaire. C'est la leçon de task-243, task-256 et task-258 :
c'est ce compteur qui a permis, sur l'écriture, de trancher entre file et
travail.

## Definition of Done

- [ ] Build passe (0 erreur), tests passent (0 échec)
- [ ] Un périmètre par envoi publie ses **phases**, chacune sommable et
      comparable d'un tir à l'autre, plus **le reste** par différence
- [ ] Un compteur donne le **nombre d'allers-retours vers le serveur mail par
      envoi** — réutiliser `mssante_mail_server_solicitations_total` (task-225)
      plutôt que d'en créer un autre, si son périmètre le permet
- [ ] `report.py` publie la **phrase attribuable** : « sur les X ms d'un envoi,
      A ms sont l'obtention de session, B ms la transmission, C ms l'archivage… »
- [ ] **Hors périmètre, rien ne coûte** : sans scope actif, ni allocation ni série
- [ ] Une absence de donnée écrit **« non relevé »**, jamais un zéro
- [ ] Tests unitaires de la décomposition, dont un cas « session réutilisée »
      (aucune ouverture) et un cas « archivage absent »
- [ ] **Aucune donnée de santé dans les étiquettes** : ni INS, ni adresse de
      destinataire, ni objet de message — littéraux d'un ensemble fini,
      **vérifié par test**
- [ ] **Contre-épreuve** : un tir `journey` à au moins deux paliers, et le
      rapport **nomme la phase dominante**. Si la décomposition n'explique pas
      les 1,3 s, le **dire** — c'est un résultat, et il désigne alors une phase
      non instrumentée

## Manual Test Plan

- Monter le banc (skill `loadtest-skill`) — **contrôler d'abord à qui appartient
  le CPU**, et que les **UID des boîtes commencent à 1**
- Seeder une petite population, purger, préchauffer
- Lancer un tir `journey` à deux paliers
- **Ce qu'il faut voir** dans le rapport : la décomposition de l'envoi et sa
  phrase attribuable, avec le nombre d'allers-retours par envoi
- Envoyer un message depuis l'application : il doit partir normalement, et une
  copie doit apparaître dans « Messages envoyés »
- Vérifier dans Seq qu'aucune étiquette ne porte d'adresse ni d'objet de message

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — observabilité interne
- **Exigences DSR honorées** : aucune — aucun changement fonctionnel
- **INS** : ⚠️ le chemin instrumenté transporte des **comptes rendus porteurs
  d'INS**. Le périmètre ne publie que des **durées**, des **nombres** et des
  **noms de phases** pris dans un ensemble fini : aucune adresse, aucun objet,
  aucun identifiant
- **Interop CI-SIS** : volet transport MSSanté — ⚠️ **l'intégrité du message
  remis est bloquante** : l'instrumentation observe, elle ne doit rien changer au
  contenu transmis ni à l'archivage
- **Habilitations** : inchangées
- **Authentification PS / Consentement** : inchangés
- **Tracé PGSSI-S** : ⚠️ l'envoi est un acte tracé ; l'instrumentation ne doit ni
  masquer ni dupliquer une entrée d'audit existante
- **Hébergement HDS** : le coût de l'instrument doit être négligeable en
  production — critère « hors périmètre, rien ne coûte » ci-dessus
- **AIPD / impact RGPD** : inchangé
