# todo-task-285.md — Clôture immédiate de la session de messagerie à la déconnexion, sur tous les pods

**Repos**: api-mail, client-angular, client-mobile, client-blazor
**Dependencies**: —
**Epic**: E009

## Objective

Quand un professionnel de santé se déconnecte, ses connexions IMAP et SMTP
MSSanté doivent tomber **immédiatement**, et pas au bout du délai d'inactivité.
Aujourd'hui elles survivent : le praticien croit être sorti, mais une session
authentifiée auprès de l'opérateur MSSanté reste ouverte en son nom pendant
plusieurs minutes.

Deux causes distinctes, à traiter ensemble :

1. **Les frontends ne préviennent pas le backend.** `client-angular` et
   `client-mobile` n'émettent aucun ordre de clôture à la déconnexion ; seul
   `client-blazor` appelle l'API, et pas systématiquement au bon moment. Le
   praticien part vers la déconnexion du proxy sans que la messagerie
   l'apprenne.
2. **L'ordre ne porte que sur un pod.** Le mécanisme de clôture existe déjà côté
   backend, mais le registre des sessions est **propre à chaque processus**.
   L'API tourne en plusieurs instances : l'ordre atterrit sur celle qui répond,
   ferme la session qu'elle détient, et laisse intactes celles des autres
   instances. Le praticien peut donc avoir des connexions ouvertes sur
   plusieurs instances et n'en voir tomber qu'une.

La US ferme les deux : les trois frontends émettent l'ordre **avant** de
quitter la session, et l'ordre atteint **toutes** les instances de l'API.

## Contexte constaté (pour l'implémentation)

- Le point d'entrée `POST /api/v1/sync/logout` existe et fonctionne — il ferme
  la session **de l'instance qui reçoit l'appel**.
- Le registre des sessions est en mémoire du processus, indexé par la paire
  (adresse MSSanté du praticien, identifiant de session cliente).
- L'identifiant de session cliente vient d'un en-tête envoyé par le client.
  **Seul `client-mobile` l'envoie aujourd'hui** (acquis de task-282) ;
  `client-angular` et `client-blazor` retombent sur l'identifiant de session du
  fournisseur d'identité. Conséquence assumée du périmètre retenu (voir règles
  métier) : sur ces deux frontends, « la session courante » vaut de fait pour la
  session d'authentification entière — deux onglets Angular du même praticien
  partagent un identifiant, donc se déconnectent ensemble.
- **Ce repli est fonctionnel aujourd'hui, mais il n'est garanti par rien.**
  Vérifié le 2026-09-01 sur deux jetons `client-angular` successifs séparés d'un
  refresh : `jti` change, l'identifiant de session du fournisseur d'identité
  reste stable. Il ne s'agit donc pas du défaut de rotation corrigé par
  task-282 — ce défaut portait sur des jetons *sans* identifiant de session, qui
  retombaient sur `jti`, unique par jeton. L'alignement des deux frontends sur
  l'en-tête fait l'objet d'une US séparée (voir `questions/task-286.md`) : il
  rendra le périmètre de la règle 2 uniforme, mais **n'est pas un prérequis** de
  cette US.
- L'infrastructure de diffusion inter-instances est déjà en place (bus de
  messages et cache distribué). Le choix du véhicule appartient à
  l'implémentation, pas à cette US.

## Règles métier

1. **L'ordre précède la déconnexion.** Le frontend contacte l'API pour ordonner
   la fin de session **avant** de purger sa session locale et avant de rediriger
   vers la déconnexion du proxy. Aucun frontend ne quitte l'écran authentifié
   sans avoir émis l'ordre.

2. **Périmètre : la session cliente courante.** L'ordre ferme la session
   identifiée par (praticien, identifiant de session cliente). Un praticien
   connecté sur un autre appareil **conserve** sa session sur cet appareil.

3. **Un échec n'emprisonne jamais le praticien.** Si l'API ne répond pas
   (délai dépassé, erreur serveur, réseau coupé), la déconnexion se poursuit
   quand même : session locale purgée, redirection vers le proxy. L'échec est
   journalisé. La fermeture reste alors garantie par le filet serveur existant
   (expiration de session et balayage périodique).

4. **L'ordre atteint toutes les instances.** Une fois l'ordre accepté, aucune
   instance de l'API ne conserve de connexion IMAP ou SMTP ouverte pour cette
   session — y compris les instances qui n'ont pas reçu l'appel.

5. **L'API n'attend pas la confirmation de toutes les instances pour répondre.**
   Elle accuse réception dès que l'ordre est émis. Le praticien ne paie pas le
   temps de propagation.

6. **Rejouer l'ordre est sans effet de bord.** Un second appel pour une session
   déjà close répond normalement, sans erreur — le frontend peut réessayer, et
   deux onglets peuvent se déconnecter en même temps.

## Risque accepté

**Une requête en vol peut rouvrir une connexion juste après l'ordre.** Le
périmètre retenu est une diffusion simple : on ferme ce qui est ouvert au
moment de l'ordre, sans marquer la session comme révoquée. Une requête partie
avant la déconnexion et arrivée après peut donc recréer une session sur une
instance. La fenêtre est courte et la session recréée retombe sur le filet
d'expiration existant. Arbitrage humain du 2026-09-01 ; à revoir si la
journalisation montre des ré-ouvertures effectives.

## Definition of Done

- [ ] Build passe sur chaque repo listé (0 erreur)
- [ ] Tests passent sur chaque repo listé (0 échec)
- [ ] Test d'intégration : l'ordre reçu par une instance ferme la session
      détenue par **une autre** instance
- [ ] Test d'intégration : l'ordre sur une session inexistante ou déjà close
      répond en succès, sans erreur (règle 6)
- [ ] Test d'intégration : la réponse de l'API n'attend pas la propagation
      (règle 5)
- [ ] >= 1 test unitaire par nouveau handler backend
- [ ] Test unitaire par frontend : la déconnexion appelle l'API **avant** de
      purger la session locale (règle 1)
- [ ] Test unitaire par frontend : la déconnexion aboutit même quand l'appel
      échoue ou expire (règle 3)
- [ ] `client-mobile` transmet son identifiant de session cliente dans l'ordre
- [ ] Évènements PGSSI-S journalisés : ordre de clôture reçu, nombre de
      sessions effectivement fermées, échec de diffusion, échec d'émission
      côté client
- [ ] Aucune donnée de santé en clair dans les logs (contenu de message, INS,
      pièce jointe, contenu CDA) — l'identification du praticien reste limitée
      à ce qu'exige l'imputabilité PGSSI-S
- [ ] `data-testid` sur le contrôle de déconnexion des trois frontends

## Manual Test Plan

**Le banc local reproduit le multi-pods** : l'AppHost lance l'API en 5
instances, c'est exactement le cas à couvrir.

1. Démarrer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
   (profil `https`). Vérifier dans le tableau de bord Aspire que les 5 instances
   de `mss-mail-api` sont vertes.
2. Démarrer un frontend :
   - mobile : `cd Client/Mobile && npm start`
   - angular : `cd Client/Angular && npm start`
   - blazor : `cd Client/Blazor && dotnet run`
3. Se connecter avec un compte MSSanté de test, ouvrir la boîte de réception et
   naviguer dans plusieurs dossiers — l'objectif est que **plusieurs** instances
   ouvrent une connexion IMAP (la répartition de charge les distribue).
4. Dans Seq (`http://localhost:5342`), relever les instances qui ont créé une
   session pour ce praticien.
5. Se déconnecter depuis le frontend.
6. **Attendu** : dans Seq, un ordre de clôture reçu, puis une fermeture de
   session sur **chacune** des instances relevées à l'étape 4 — en quelques
   secondes, sans attendre le délai d'inactivité de 5 minutes.
7. **Attendu** : côté opérateur MSSanté, plus aucune session IMAP ouverte pour
   ce compte (visible dans les journaux du serveur de test).
8. Répéter les étapes 2 à 5 sur les deux autres frontends.
9. **Cas dégradé** : arrêter le backend, puis se déconnecter depuis le
   frontend. **Attendu** : la déconnexion aboutit, le praticien arrive bien sur
   l'écran de connexion, et l'échec est visible dans la console du frontend.
10. **Cas multi-appareils** : se connecter sur mobile ET sur angular avec le
    même compte, se déconnecter du mobile. **Attendu** : la session angular
    reste fonctionnelle (règle 2).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors périmètre fonctionnel DSR — exigence de sécurité
  transverse au socle MSSanté déjà référencé
- **Exigences DSR honorées** : aucune exigence DSR fonctionnelle nouvelle. La US
  sert la PGSSI-S (§ authentification, § journalisation, § imputabilité) et
  réduit la durée de vie d'une session MSSanté authentifiée sans utilisateur.
  **Le rattachement DSR précis est à confirmer avec le référent Ségur** — je ne
  cite pas de code d'exigence que je n'ai pas vérifié.
- **INS** : non applicable — la déconnexion ne manipule aucune donnée patient
  ni aucun identifiant national de santé.
- **Authentification PS** : PSC / e-CPS via le proxy d'identité, niveau eIDAS
  substantiel. La US ne modifie pas l'authentification ; elle traite sa
  terminaison.
- **Habilitations** : non applicable — tout praticien authentifié peut clore sa
  propre session, et seulement la sienne. L'ordre ne peut pas viser la session
  d'un autre praticien.
- **Interop CI-SIS** : non applicable — aucun échange métier, aucun document.
- **Tracé PGSSI-S** : ordre de clôture reçu (praticien, session, horodatage),
  nombre de sessions effectivement fermées, échec de diffusion inter-instances,
  échec d'émission côté client. Conservation alignée sur les journaux d'accès
  existants de l'API (6 ans).
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui — l'API héberge des données de santé à caractère
  personnel (contenu des messages MSSanté). La US ne crée aucun nouveau
  traitement de DSCP ; elle raccourcit la fenêtre d'exposition d'une session
  ouverte.
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement de données
  personnelles. Effet favorable sur la minimisation (durée de conservation
  d'une session active réduite).
- **MSSanté** : les connexions closes sont celles de l'API LPS de l'opérateur
  MSSanté (adresse personnelle PS). Aucun en-tête ni certificat n'est modifié
  par cette US.
